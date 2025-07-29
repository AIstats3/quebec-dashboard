import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib import pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc
import matplotlib.colors as mcolors

def get_points(event):
    if 'm' in event:
        return 0 ##Discount misses
    elif any(x in event for x in ['z5','z6','z7','z8','z9']):
        return 3 ##Threes
    elif any(x in event for x in ['z1','z2','z3','z4']):
        return 2 ##Layups and middies
    elif 'f' in event:
        return 1 ##Free throws
    return 0 ##Non-scoring events

##Function to convert minutes to mm:ss format
def minutes_to_time_format(minutes_float):
    ##Get total seconds
    total_seconds = int(minutes_float * 60)
    
    ##Calculate minutes and seconds
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    ##Format as mm:ss
    return f"{minutes:02}:{seconds:02}"
    
##Function to convert seconds to mm:ss format
def seconds_to_time_format(seconds_int):
    
    ##Calculate minutes and seconds
    minutes = seconds_int // 60
    seconds = seconds_int % 60
    
    ##Format as mm:ss
    return f"{minutes:02}:{seconds:02}"
    
##Function to convert time format to seconds
def time_format_to_seconds(time_format):
    minutes = int(time_format.rsplit(':')[0])
    seconds = int(time_format.rsplit(':')[1])
    seconds += minutes * 60
    return seconds


def get_rotation_df(events):
    ##Augment play by play data to have necassary columns for +/- calculations
    events['quarter'].ffill(inplace=True)
    events['lineup'].ffill(inplace=True)
    if type(events['lineup'][0]) != list:
        events['lineup'] = events['lineup'].apply(lambda x: x.split('/'))
    events['time'].ffill(inplace=True)
    events.fillna('', inplace=True)
    
    ##Get time as integer and compute time elapsed
    events['time_int'] = events['time'].apply(lambda x: 60 * int(x.split(':')[0]) + int(x.split(':')[1]))
    events['time_elapsed'] = 600 - events['time_int']
    def adjust_time(row):
        period_offsets = {
            'q2': 600, 'q3': 1200, 'q4': 1800,
            'OT': 2400, 'OT2': 2700, 'OT3': 3000
        }
        return row['time_elapsed'] + period_offsets.get(row['quarter'], 0)


    events['time_elapsed'] = events.apply(
    lambda row: (600 - row['time_int']) if not row['quarter'].startswith('OT') else (300 - row['time_ing']),
    axis=1
    )
    events['time_elapsed'] = events.apply(adjust_time, axis=1)
    ##Get current points for both teams at each point throughout the game and the margin between them from ConU perspective
    events['Q_points'] = 0
    events['Opp_points'] = 0
    concordia_score = 0
    opponent_score = 0

    for i, row in events.iterrows():
        points = get_points(row['event'])
        if row['player'].startswith('-'):  ##Opponent events
            opponent_score += points
        elif ~row['player'].startswith('-'):  ##Concordia events
            concordia_score += points

        ##Update score columns
        events.at[i, 'Q_points'] = concordia_score
        events.at[i, 'Opp_points'] = opponent_score
    events['Score_margin'] = events['Q_points'] - events['Opp_points']

    
    ##Take the rows that we need for a rotation df, as a copy so we dont mess anything up with shifts and calcs
    subs_df = events.loc[events['event'] == 'sub'][['lineup','quarter','Q_points',
                                     'Opp_points','Score_margin','time_int','time_elapsed']].copy()
    ##Reset the index
    subs_df.reset_index(inplace=True, drop=True)
    ##Shift the points and score since they reflect the game state AFTER each shift
    subs_df[['Q_points','Opp_points','Score_margin']] = subs_df[['Q_points','Opp_points','Score_margin']].shift(-1)
    ##Define times out with a shift as well
    subs_df[['Time_out','Time_out_elapsed']] = subs_df[['time_int','time_elapsed']].shift(-1)
    ##Calculate +/- to see how each lineup changed the game state
    subs_df['+/-'] = subs_df['Score_margin'] - subs_df['Score_margin'].shift(1)
    ##Set +/- of first row since shift method will miss it
    subs_df.loc[0,'+/-'] = subs_df.loc[0,'Score_margin']
    ##Drop the last row, we just put it there to track game state at end of game
    subs_df.drop(len(subs_df)-1, inplace=True)
    ##Rename columns
    subs_df.rename(columns={'time_int':'Time_in','time_elapsed':'Time_in_elapsed'}, inplace=True)
    ##Reset time elapsed to be in terms of minutes not seconds
    subs_df[['Time_in_elapsed','Time_out_elapsed']] = subs_df[['Time_in_elapsed','Time_out_elapsed']].apply(lambda x: x/60)
    ##Calculate shift length
    subs_df['Shift_length'] = subs_df['Time_out_elapsed'] - subs_df['Time_in_elapsed']
    ##Convert Times (not time elapsed) into time format
    subs_df['Time_in'] = subs_df['Time_in'].apply(seconds_to_time_format)
    subs_df['Time_out'] = subs_df['Time_out'].apply(int).apply(seconds_to_time_format)
    ##Change all '10:00' values in Time_out to '00:00' for clarity
    subs_df['Time_out'] = subs_df['Time_out'].replace('10:00', '00:00')

    ##Make +/- an integer
    subs_df['+/-'] = subs_df['+/-'].apply(int)

    
   
    
    return subs_df


def get_shot_zone_stats(event_df):
    # Define individual shot zones
    shot_zones = {
        "right_corner_three": "z9",
        "right_wing_three": "z8",
        "center_three": "z7",
        "left_wing_three": "z6",
        "left_corner_three": "z5",
        "right_midrange": "z4",
        "center_midrange": "z3",
        "left_midrange": "z2",
        "restricted_area": "z1"
    }

    # Define aggregated zones
    aggregated_zones = {
        "layups": ["z1"],
        "midranges": ["z2", "z3", "z4"],
        "3FG": ["z5", "z6", "z7", "z8", "z9"],
        "2FG":["z1","z2","z3","z4"],
        "FG":["z1","z2","z3","z4","z5", "z6", "z7", "z8", "z9"],
    }

    # Initialize dictionary for storing stats
    shot_zone_stats = {}

    # Compute stats for individual shot zones
    for zone_name, zone_code in shot_zones.items():
        in_zone = event_df['event'].str.contains(zone_code, na=False)
        made = in_zone & ~event_df['event'].str.contains('m', na=False)
        attempted = in_zone

        FG = made.sum()
        FGA = attempted.sum()
        FG_percent = 100 * (FG / FGA) if FGA > 0 else 0  # Avoid division by zero

        shot_zone_stats[zone_name] = {"FG": FG, "FGA": FGA, "FG%": round(FG_percent, 2)}

    # Compute stats for aggregated shot zones
    for agg_name, zone_codes in aggregated_zones.items():
        in_zone = event_df['event'].str.contains('|'.join(zone_codes), na=False)
        made = in_zone & ~event_df['event'].str.contains('m', na=False)
        attempted = in_zone

        FG = made.sum()
        FGA = attempted.sum()
        FG_percent = FG / FGA if FGA > 0 else 0  # Avoid division by zero

        shot_zone_stats[agg_name] = {"FG": FG, "FGA": FGA, "FG%": round(FG_percent, 3)}

    return shot_zone_stats


def get_shot_clock_stats(events_df):
    partition_stats = {}
    
    partitions = {
        "24-18": events_df[(events_df["shotclock"] <= 24) & (events_df["shotclock"] > 18)],
        "18-6": events_df[(events_df["shotclock"] <= 18) & (events_df["shotclock"] > 6)],
        "6-0": events_df[(events_df["shotclock"] <= 6) & (events_df["shotclock"] >= 0)]
    }

    total_attempts = sum(events_df["event"].str.contains("c"))  # Count total FG attempts
    total_fg = total_2fg = total_3fg = total_to = 0
    total_fga = total_2fga = total_3fga = 0

    for label, subset in partitions.items():
        stats = get_shot_zone_stats(subset)
        attempts = sum(subset["event"].str.contains("c"))  # FG attempts in this partition
        attempt_pct = round(100 * attempts / total_attempts, 2) if total_attempts > 0 else 0  # Compute percentage

        fg, fga = stats["FG"]["FG"], stats["FG"]["FGA"]
        fg2, fga2 = stats["2FG"]["FG"], stats["2FG"]["FGA"]
        fg3, fga3 = stats["3FG"]["FG"], stats["3FG"]["FGA"]
        to_count = subset["event"].str.contains("TO").sum()

        partition_stats[label] = {
            "FG": f"{fg}-{fga}",
            "FG%": f"{round(100 * stats['FG']['FG%'], 2)}%",
            "2FG": f"{fg2}-{fga2}",
            "2FG%": f"{round(100 * stats['2FG']['FG%'], 2)}%",
            "3FG": f"{fg3}-{fga3}",
            "3FG%": f"{round(100 * stats['3FG']['FG%'], 2)}%",
            "TO": to_count,
            "Attempt%": f"{attempt_pct}%"
        }

        # Accumulate totals
        total_fg += fg
        total_fga += fga
        total_2fg += fg2
        total_2fga += fga2
        total_3fg += fg3
        total_3fga += fga3
        total_to += to_count

    # Compute total percentages
    total_fg_pct = round(100 * total_fg / total_fga, 2) if total_fga > 0 else 0
    total_2fg_pct = round(100 * total_2fg / total_2fga, 2) if total_2fga > 0 else 0
    total_3fg_pct = round(100 * total_3fg / total_3fga, 2) if total_3fga > 0 else 0

    partition_stats["Total"] = {
        "FG": f"{total_fg}-{total_fga}",
        "FG%": f"{total_fg_pct}%",
        "2FG": f"{total_2fg}-{total_2fga}",
        "2FG%": f"{total_2fg_pct}%",
        "3FG": f"{total_3fg}-{total_3fga}",
        "3FG%": f"{total_3fg_pct}%",
        "TO": total_to,
        "Attempt%": "100%"
    }

    return pd.DataFrame(partition_stats).T


def get_contested_shot_stats(events_df):
    partition_stats = {}
    
    categories = {
        "Wide Open": events_df[events_df["event"].str.contains("c1")],
        "Open": events_df[events_df["event"].str.contains("c2")],
        "Contested": events_df[events_df["event"].str.contains("c3")],
        "Heavily Contested": events_df[events_df["event"].str.contains("c4")]
    }
    
    total_attempts = sum(events_df["event"].str.contains("c"))  # Count total FG attempts
    total_fg = total_2fg = total_3fg = 0
    total_fga = total_2fga = total_3fga = 0

    for category, subset in categories.items():
        stats = get_shot_zone_stats(subset)
        attempts = sum(subset["event"].str.contains("c"))  # FG attempts in this category
        attempt_pct = round(100 * attempts / total_attempts, 2) if total_attempts > 0 else 0  # Compute percentage

        fg, fga = stats["FG"]["FG"], stats["FG"]["FGA"]
        fg2, fga2 = stats["2FG"]["FG"], stats["2FG"]["FGA"]
        fg3, fga3 = stats["3FG"]["FG"], stats["3FG"]["FGA"]

        partition_stats[category] = {
            "FG": f"{fg}-{fga}",
            "FG%": f"{round(100 * stats['FG']['FG%'], 2)}%",
            "2FG": f"{fg2}-{fga2}",
            "2FG%": f"{round(100 * stats['2FG']['FG%'], 2)}%",
            "3FG": f"{fg3}-{fga3}",
            "3FG%": f"{round(100 * stats['3FG']['FG%'], 2)}%",
            "Attempt%": f"{attempt_pct}%"
        }

        # Accumulate totals
        total_fg += fg
        total_fga += fga
        total_2fg += fg2
        total_2fga += fga2
        total_3fg += fg3
        total_3fga += fga3

    # Compute total percentages
    total_fg_pct = round(100 * total_fg / total_fga, 2) if total_fga > 0 else 0
    total_2fg_pct = round(100 * total_2fg / total_2fga, 2) if total_2fga > 0 else 0
    total_3fg_pct = round(100 * total_3fg / total_3fga, 2) if total_3fga > 0 else 0

    partition_stats["Total"] = {
        "FG": f"{total_fg}-{total_fga}",
        "FG%": f"{total_fg_pct}%",
        "2FG": f"{total_2fg}-{total_2fga}",
        "2FG%": f"{total_2fg_pct}%",
        "3FG": f"{total_3fg}-{total_3fga}",
        "3FG%": f"{total_3fg_pct}%",
        "Attempt%": "100%"
    }

    return pd.DataFrame(partition_stats).T

def get_contested_shot_zone_stats(events_df):
    partition_stats = {}
    
    categories = {
        "Wide Open": events_df[events_df["event"].str.contains("c1")],
        "Open": events_df[events_df["event"].str.contains("c2")],
        "Contested": events_df[events_df["event"].str.contains("c3")],
        "Heavily Contested": events_df[events_df["event"].str.contains("c4")]
    }
    
    total_attempts = sum(events_df["event"].str.contains("c"))  # Count total FG attempts
    total_fg = total_2fg = total_3fg = 0
    total_fga = total_2fga = total_3fga = 0

    for category, subset in categories.items():
        stats = get_shot_zone_stats(subset)
        attempts = sum(subset["event"].str.contains("c"))  # FG attempts in this category
        attempt_pct = round(100 * attempts / total_attempts, 2) if total_attempts > 0 else 0  # Compute percentage

        fg, fga = stats["FG"]["FG"], stats["FG"]["FGA"]
        fg2, fga2 = stats["2FG"]["FG"], stats["2FG"]["FGA"]
        fg3, fga3 = stats["3FG"]["FG"], stats["3FG"]["FGA"]

        partition_stats[category] = {
            "FG": f"{fg}-{fga}",
            "FG%": f"{round(100 * stats['FG']['FG%'], 2)}%",
            "2FG": f"{fg2}-{fga2}",
            "2FG%": f"{round(100 * stats['2FG']['FG%'], 2)}%",
            "3FG": f"{fg3}-{fga3}",
            "3FG%": f"{round(100 * stats['3FG']['FG%'], 2)}%",
            "Attempt%": f"{attempt_pct}%"
        }

        # Accumulate totals
        total_fg += fg
        total_fga += fga
        total_2fg += fg2
        total_2fga += fga2
        total_3fg += fg3
        total_3fga += fga3

    # Compute total percentages
    total_fg_pct = round(100 * total_fg / total_fga, 2) if total_fga > 0 else 0
    total_2fg_pct = round(100 * total_2fg / total_2fga, 2) if total_2fga > 0 else 0
    total_3fg_pct = round(100 * total_3fg / total_3fga, 2) if total_3fga > 0 else 0

    partition_stats["Total"] = {
        "FG": f"{total_fg}-{total_fga}",
        "FG%": f"{total_fg_pct}%",
        "2FG": f"{total_2fg}-{total_2fga}",
        "2FG%": f"{total_2fg_pct}%",
        "3FG": f"{total_3fg}-{total_3fga}",
        "3FG%": f"{total_3fg_pct}%",
        "Attempt%": "100%"
    }

    return pd.DataFrame(partition_stats).T



def annotate_shot_zones(shot_zone_data, ax = None):

        

    ## Initialize Figure ##
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
        
    draw_shot_zones(ax)

    xy_dict = {
        'restricted_area':{'x':-110,'y':-55},
        'left_corner_three':{'x':-750,'y':50},
        'right_corner_three':{'x':750,'y':50},
        'center_three':{'x':0,'y':800},
        'left_wing_three':{'x':-600,'y':600},
        'right_wing_three':{'x':600,'y':600},
        'center_midrange':{'x':0,'y':400},
        'left_midrange':{'x':-425,'y':150},
        'right_midrange':{'x':425,'y':150}


    }
    cmap = plt.cm.bwr

    # Define dictionary normalization scales relative to shot location
    norm_dict = {
        'restricted_area':mcolors.Normalize(vmin=40, vmax=60),
        'left_corner_three':mcolors.Normalize(vmin=15, vmax=35),
        'right_corner_three':mcolors.Normalize(vmin=15, vmax=35),
        'center_three':mcolors.Normalize(vmin=15, vmax=35),
        'left_wing_three':mcolors.Normalize(vmin=15, vmax=35),
        'right_wing_three':mcolors.Normalize(vmin=15, vmax=35),
        'center_midrange':mcolors.Normalize(vmin=20, vmax=40),
        'left_midrange':mcolors.Normalize(vmin=20, vmax=40),
        'right_midrange':mcolors.Normalize(vmin=20, vmax=40)


    }

    for key in xy_dict.keys():
        FG = shot_zone_data[key]['FG']
        FGA = shot_zone_data[key]['FGA']
        FGp = shot_zone_data[key]['FG%']
        
        ax.annotate(f'{FG}/{FGA}\n{FGp}%', (xy_dict[key]['x'], xy_dict[key]['y']-25), ha='center',va='center',
                    color='black', fontweight=600)
        i_circle = Circle((xy_dict[key]['x'],xy_dict[key]['y']),radius=90, fill=True, fc=cmap(norm_dict[key](FGp)) , alpha=0.25,zorder=15)
        o_circle = Circle((xy_dict[key]['x'],xy_dict[key]['y']),radius=90, fill=False, ec='black', alpha=1)
        ax.add_patch(i_circle)
        ax.add_patch(o_circle)

    return ax



##Functions for drawing


def draw_rotation_sheet(OT=False, OT2=False, OT3=False, w=16, h=8, fs=11, number_of_lineups = 20, ax = None):
    created_fig = False
    
    ##Create new fig and ax only if not provided
    if ax is None:
        fig, ax = plt.subplots(figsize=(w, h))
        created_fig = True
    else:
        fig = ax.figure
        
        
    if OT:
        w += 0.5
        h +=0.25
    if OT2:
        w += 1
        h +=0.5
    if OT3:
        w += 1.5
        h +=0.75
        
  
        
    # Create a rectangle patch
    rectangle_width, rectangle_height = 40, number_of_lineups * 2
    if OT:
        rectangle_width += 5
    if OT2:
        rectangle_width += 10
    if OT3:
        rectangle_width += 15
        
    ##Set up and add rectangle to ax    
    rectangle_width = 40 + (5 if OT else 0) + (5 if OT2 else 0) + (5 if OT3 else 0)
    rectangle_height = number_of_lineups * 2
    rectangle = Rectangle((0, 0), rectangle_width, rectangle_height, linewidth=2, edgecolor='black', facecolor='none')
    ax.add_patch(rectangle)

    ##Set axis limits to allow for annotation in the margins
    ax.set_xlim(0, rectangle_width+15)
    ax.set_ylim(-5, rectangle_height+5)

    ##Titles and annotations
    plt.title('Rotation Sheet', fontsize=16)
    plt.annotate('Lineup',(rectangle_width+10,rectangle_height+1),fontsize=fs+1)
    plt.annotate('Totals',(rectangle_width+3,rectangle_height+3),fontsize=fs+5)
    plt.annotate('Minutes',(rectangle_width+1,rectangle_height+1),fontsize=fs+5)
    plt.annotate('+/-',(rectangle_width+6,rectangle_height+1),fontsize=fs+5)

    # Add minute markers
    for i in range(4):
        for j in range(1, 11):
            ax.annotate(str(j), (j - 1 + 10 * i, rectangle_height + 1), ha='center', va='center', fontsize=fs)
    
    
    ##Add quarter markers and annotations
    ax.annotate('Q1', (0, rectangle_height + 4), ha='center', va='center', fontsize=fs + 5)
    for i, label in zip([10, 20, 30], ['Q2', 'Q3', 'Q4']):
        ax.vlines(i, 0, rectangle_height, color='black', linestyle='dotted', alpha=0.2)
        ax.annotate(label, (i, rectangle_height + 4), ha='center', va='center', fontsize=fs + 5)


    
    ##Handle OT
    for ot_idx, enabled in enumerate([OT, OT2, OT3], start=1):
        if enabled:
            base = 40
            for i in range(ot_idx):
                x = base + i * 5
                for j in range(1, 6):
                    ax.annotate(str(j), (j - 1 + x, rectangle_height + 1), ha='center', va='center', fontsize=fs)
                ax.vlines(x, 0, rectangle_height, color='black', linestyle='dashed', alpha=0.2)
                ax.annotate(f'OT{i+1}' if i > 0 else 'OT', (x, rectangle_height + 4), ha='center', va='center', fontsize=fs + 5)


    ##Clear axis for clarity
    ax.axis('off')
    
    ##Return the axis and the figure
    return fig, ax if created_fig else ax


def draw_half_court(ax=None, color='black', lw=1, outer_lines=True):
    """
    FIBA basketball court dimensions:
    https://www.msfsports.com.au/basketball-court-dimensions/
    It seems like the Euroleauge API returns the shooting positions
    in resolution of 1cm x 1cm.
    """
    # If an axes object isn't provided to plot onto, just get current one
    if ax is None:
        ax = plt.gca()

    # Create the various parts of an NBA basketball court

    # Create the basketball hoop
    # Diameter of a hoop is 45.72cm so it has a radius 45.72/2 cms
    hoop = Circle((0, 0), radius=45.72 / 2, linewidth=lw, color=color,
                  fill=False)

    # Create backboard
    backboard = Rectangle((-90, -157.5 + 120), 180, -1, linewidth=lw,
                          color=color)

    # The paint
    # Create the outer box of the paint
    outer_box = Rectangle((-490 / 2, -157.5), 490, 580, linewidth=lw,
                          color=color, fill=False)
    # Create the inner box of the paint, widt=12ft, height=19ft
    inner_box = Rectangle((-360 / 2, -157.5), 360, 580, linewidth=lw,
                          color=color, fill=False)

    # Create free throw top arc
    top_free_throw = Arc((0, 580 - 157.5), 360, 360, theta1=0, theta2=180,
                         linewidth=lw, color=color, fill=False)
    # Create free throw bottom arc
    bottom_free_throw = Arc((0, 580 - 157.5), 360, 360, theta1=180, theta2=0,
                            linewidth=lw, color=color, linestyle='dashed')
    # Restricted Zone, it is an arc with 4ft radius from center of the hoop
    restricted = Arc((0, 0), 2 * 125, 2 * 125, theta1=0, theta2=180,
                     linewidth=lw, color=color)

    # Three point line
    # Create the side 3pt lines
    corner_three_a = Rectangle((-750 + 90, -157.5), 0, 305, linewidth=lw,
                               color=color)
    corner_three_b = Rectangle((750 - 90, -157.5), 0, 305, linewidth=lw,
                               color=color)
    # 3pt arc - center of arc will be the hoop, arc is 23'9" away from hoop
    # I just played around with the theta values until they lined up with the
    # threes
    three_arc = Arc((0, 0), 2 * 675, 2 * 675, theta1=12, theta2=167.5,
                    linewidth=lw, color=color)

    # Center Court
    center_outer_arc = Arc((0, 1400-157.5), 2 * 180, 2 * 180, theta1=180,
                           theta2=0, linewidth=lw, color=color)

    # List of the court elements to be plotted onto the axes
    court_elements = [hoop, backboard, outer_box,
                      restricted, top_free_throw, bottom_free_throw,
                      corner_three_a, corner_three_b, three_arc,
                      center_outer_arc]
    if outer_lines:
        # Draw the half court line, baseline and side out bound lines
        outer_lines = Rectangle((-750, -157.5), 1500, 1400, linewidth=lw,
                                color=color, fill=False)
        court_elements.append(outer_lines)

    # Add the court elements onto the axes
    for element in court_elements:
        ax.add_patch(element)


    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_xlim(-900, 900)
    ax.set_ylim(1242.5, -157.5)
    
    ax.axis('off')


    return ax


def draw_shot_zones(ax=None):
    if ax is None:
        ax = draw_half_court()
    else:
        draw_half_court(ax)
        
    ##Draw the shooting zones on the half court
    ##degree to radian factor
    a = math.pi / 180
    ##inner partition angle
    i_angle = 50
    ##outer partition angle
    o_angle= 65


    ra_marker = Arc((0,-157.5),480,560,theta1=0,theta2=180, color = 'black', ls='--',lw=1)
    ax.add_patch(ra_marker)
    right_inner = ax.plot([125*math.cos(i_angle*a),675*math.cos(i_angle*a)],[125*math.sin(i_angle*a),675*math.sin(i_angle*a)], color = 'black', ls='--',lw=1)
    left_inner = ax.plot([-125*math.cos(i_angle*a),-675*math.cos(i_angle*a)],[125*math.sin(i_angle*a),675*math.sin(i_angle*a)], color = 'black', ls='--',lw=1)
    right_corner_three = ax.plot([750,604],[300,300], color = 'black', ls='--',lw=1)
    left_corner_three = ax.plot([-750,-604],[300,300], color = 'black', ls='--',lw=1)
    right_wing_three = ax.plot([675*math.cos(o_angle*a),1500*math.cos(o_angle*a)],[675*math.sin(o_angle*a),1500*math.sin(o_angle*a)], color = 'black', ls='--',lw=1)
    left_wing_three = ax.plot([-675*math.cos(o_angle*a),-1500*math.cos(o_angle*a)],[675*math.sin(o_angle*a),1500*math.sin(o_angle*a)], color = 'black', ls='--',lw=1)

        
    return ax
    


