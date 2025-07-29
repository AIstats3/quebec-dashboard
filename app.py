from flask import Flask, render_template, request, jsonify
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import ast
import io, base64
from dashboard.core_functions import *
from helpers import player_number_dict
##Init Flask app
app = Flask(__name__, template_folder='templates', static_folder="static")

##Define paths
rotation_dfs_dir = os.path.join("dashboard", "rotation_dfs")
game_files_dir = os.path.join("dashboard", "game_files")
box_scores_dir = os.path.join("dashboard", "box_scores")

##F'n to show available games in dropdown
@app.route('/')
def index():
  game_files = sorted(f for f in os.listdir(game_files_dir) if f.endswith('.csv'))
  player_numbers = list(player_number_dict.keys())
  return render_template(
    'index.html',
    game_files=game_files,
    player_number_dict=player_number_dict,
    player_numbers=player_numbers
  )

@app.route('/get_lineup_data', methods=['POST'])
def get_lineup_data():
  """Return aggregated lineup statistics for selected games and players"""
  ##Input validation
  try:
    selected_games = request.json.get("games", [])
    selected_players = request.json.get("players", [])
    selected_players = set(map(float, selected_players)) if selected_players else set()
  except:
    return jsonify({"error":"Invalid input format"}), 400
  
  ##Load rotation dataframes
  dataframes = []
  for game in selected_games:
    ##get corresponding rotation_df filename
    rotation_df_filename = game.replace(".csv", "_rotation.csv")
    full_path = os.path.join(rotation_dfs_dir, rotation_df_filename)

    if not os.path.exists(full_path):
      app.logger.warning(f"Missing rotation file: {rotation_df_filename}")
      continue
    try:
      ##Load file if it exists
      df = pd.read_csv(full_path, sep='|')
      ##Convert stringified lists
      df['lineup'] = df['lineup'].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else x
      )
      dataframes.append(df)
    except Exception as e:
      app.logger.error(f"Failed to load or parse {rotation_df_filename}: {e}")

  if not dataframes:
    return jsonify([])
    
  ##Combine and filter data
  ##Combine
  combined_df = pd.concat(dataframes, ignore_index=True)
  ##Filter for players
  if selected_players:
    combined_df = combined_df[combined_df['lineup'].apply(
      lambda lineup: selected_players.issubset(set(map(float, lineup)))
    )]
  
  ##Aggregate and format
  combined_df['lineup'] = combined_df['lineup'].apply(tuple) ##Make hashable for grouping
  grouped = (
    combined_df
    .groupby('lineup')
    .agg({'+/-':'sum','Shift_length':'sum'})
    .reset_index()
    .sort_values(by='Shift_length', ascending=False)
  )
  ##Final formatting
  output_df = grouped[['lineup', 'Shift_length', '+/-']]
  total_row = {'lineup':'Total','Shift_length':output_df['Shift_length'].sum(), '+/-':output_df['+/-'].sum()}
  output_df = pd.concat([pd.DataFrame([total_row]), output_df], ignore_index=True)
  output_df['Shift_length'] = output_df['Shift_length'].apply(minutes_to_time_format)

  return output_df.to_json(orient="records")


@app.route('/get_shooting_fig', methods=['POST'])
def get_shooting_fig():
  try:
    selected_games = request.json.get("games", [])
    selected_players = request.json.get("players", [])
  except:
    return jsonify({"error":"Invalid input format"}), 400
  
  dataframes = []
  for game in selected_games:
    full_path = os.path.join(game_files_dir, game)
    if os.path.exists(full_path):
      df = pd.read_csv(full_path, dtype={'player':'string'})
      dataframes.append(df)
    else:
      print(f"File not found: {full_path}")

        # If no dataframes loaded, return empty response
  if not dataframes:
      print("No valid game files loaded.")
      return jsonify([])
  ##Combine game data
  combined = pd.concat(dataframes, ignore_index=True)

  if selected_players:
    print(selected_players)
    if 'All Quebec' in selected_players:
      combined = combined[~combined['player'].str.startswith('-')]
    elif 'All Opponent' in selected_players:
      combined = combined[combined['player'].str.startswith('-')]
    else:
      combined = combined[combined['player'].isin(selected_players)]
  if combined.empty:
    return jsonify({"error": "No data found for selected filters"}), 400
  

  shooting_data = get_shot_zone_stats(combined)

  fig, ax = plt.subplots(figsize=(10,8))
  annotate_shot_zones(shooting_data, ax)

  buf = io.BytesIO()
  fig.savefig(buf, format='png')
  plt.close(fig)
  buf.seek(0)
  img_base64 = base64.b64encode(buf.read()).decode('utf-8')

  return jsonify({'image': img_base64})

@app.route('/get_box_data', methods=['POST'])
def get_box_data():
  ##Input validation
  try:
    selected_games = request.json.get("games", [])
  except:
    return jsonify({"error":"Invalid input format"}), 400
  
  dataframes = []
  for game in selected_games:
    box_score_filename = game.replace('.csv', '_full_box.csv')
    full_path = os.path.join(box_scores_dir, box_score_filename)
    if not os.path.exists(full_path):
      app.logger.warning(f"Missing rotation file: {box_score_filename}")
      continue
    try:
      ##Load file if it exists
      df = pd.read_csv(full_path)
      dataframes.append(df)
    except Exception as e:
      app.logger.error(f"Failed to load or parse {box_score_filename}: {e}")

  ##Combine data
  combined_df = pd.concat(dataframes, ignore_index=True)

  combined_box = combined_df.groupby('player').sum()
  combined_box = combined_box.reset_index()
  combined_box['Minutes'] = combined_box['Minutes'].apply(minutes_to_time_format)
  combined_box = combined_box.iloc[:, [0,17,8,9,10,11,12,13,14,7,1,2,3,4,5,6,15,16]]
  return combined_box.to_json(orient='records')
  



if __name__ == '__main__':
  app.run(debug=True, port=5050)