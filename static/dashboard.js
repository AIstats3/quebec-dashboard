// Function Definitions

//Tab Switchin Function
//Function to handle switching between tabs on the page, i.e navigate between different types of statistics
function handleTabSwitching() {
  const tabs = document.querySelectorAll('.tab-button');
  const sections = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab; // Get the target section from the tab's dataset
      sections.forEach(section => section.style.display = 'none'); //Hide all sections
      document.getElementById(target).style.display = 'block';
    });
  });
}

// Dropdown Toggle Function
//This function toggles the visibility of dropdown menus (for game selection, player selection, etc.) when the dropdown button is clicked.
function toggleDropdown(dropdownToggle, dropdown) {
  dropdownToggle.addEventListener('click', (event) => {
    console.log("Dropdown button clicked");
    dropdown.classList.toggle('show');
  })
}

// Select All Checkbox for Games
//This function manages the "Select All" checkbox for the game selection dropdown. When this checkbox is checked/unchecked, it will check/uncheck all the individual game checkboxes.
function handleSelectAll(selectAll, gameDropdown) {
  selectAll.addEventListener('change', () => {
    const checkboxes = gameDropdown.querySelectorAll('input[name="game"]');
    checkboxes.forEach(cb => cb.checked = selectAll.checked); // Check/uncheck all checkboxes
  });
}

// Close Dropdown on Outside Click
function closeDropdownOnOutsideClick(dropdownToggle, dropdown) {
  document.addEventListener('click', (event) => {
    const isClickInside = dropdown.contains(event.target) || dropdownToggle.contains(event.target);
    if (!isClickInside) {
      dropdown.classList.remove('show');
    }
  })
}

// Disable Submit Buttons During Data Fetch
function toggleSubmitButton(formId, isDisabled) {
  const submitButton = document.querySelector(`#${formId} button[type="submit"]`);
  submitButton.disabled = isDisabled; //Enable/disable submit button
}

// Render Table Function
//This function renders the data received from the server in a table format. It dynamically creates the HTML structure for the table and inserts it into the designated container.
function renderTable(data, tableId) {
  const table = document.getElementById(tableId);
  table.innerHTML = '';

  if (!data || data.length === 0) {
    table.innerHTML = '<p>No data available.</p>';
    return;
  }

  // Build table structure
  const thead = document.createElement('thead');
  const tbody = document.createElement('tbody');

  const columns = Object.keys(data[0]);

  const headerRow = document.createElement('tr');
  columns.forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;

    // Add sort button for specific columns
    const sortableColumns = ['oreb', 'dreb', 'ast', 'blk', 'stl', 'foul', 'treb', 'pts',
       'FG', 'FGA', '3FG', '3FGA', 'FT', 'FTA', 'TO', '+/-', 'Minutes', 'FG%','3FG%','FT%']
    if (sortableColumns.includes(col) || sortableColumns.includes(col.toLowerCase())) {
      const sortBtn = document.createElement('button');
      sortBtn.textContent = '↕';
      sortBtn.classList.add('sort-btn');
      sortBtn.addEventListener('click', () => sortTableByColumn(tableId, col));
      th.appendChild(sortBtn);
    }

    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);

  data.forEach((row, index) => {
    const tr = document.createElement('tr');

    // Bold total row (assumed to be first row)
    if (index === 0) {
      tr.classList.add('total-row');
    }

    columns.forEach(col => {
      const td = document.createElement('td');
      td.textContent = row[col];
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
}
// Function to handle sorting the table
const sortState = {}; // Global object to track column sort order

function parseDuration(timeStr) {
  const [minStr, secStr] = timeStr.trim().split(':');
  const minutes = parseInt(minStr, 10);
  const seconds = parseInt(secStr, 10);
  return minutes * 60 + seconds;
}

function sortTableByColumn(tableId, columnName) {
  const table = document.getElementById(tableId);
  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');

  const headerCells = Array.from(thead.querySelectorAll('th'));
  const colIndex = headerCells.findIndex(th => th.textContent.includes(columnName));
  if (colIndex === -1) return;

  const rows = Array.from(tbody.querySelectorAll('tr'));
  const totalRow = rows[0]; // Keep the first row as "Total"
  const dataRows = rows.slice(1); // Sort only data rows

  // Toggle sort direction
  const currentState = sortState[columnName] || 'desc';
  const newState = currentState === 'asc' ? 'desc' : 'asc';
  sortState[columnName] = newState;

  // Custom parser for Shift_length column
  const parseValue = (text) => {
    if (columnName === 'Minutes') {
      return parseDuration(text.trim());
    } else {
      return parseFloat(text.trim()) || 0;
    }
  }

  // Sort logic
  dataRows.sort((a, b) => {
    const aVal = parseValue(a.cells[colIndex].textContent) || 0;
    const bVal = parseValue(b.cells[colIndex].textContent) || 0;
    return newState === 'asc' ? aVal - bVal : bVal - aVal;
  });

  // Re-render
  tbody.innerHTML = '';
  tbody.appendChild(totalRow);
  dataRows.forEach(row => tbody.appendChild(row));
}

//Handle Lineup Form Submission
function handleLineupFormSubmission(form, tableDiv) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const selectedFiles = Array.from(form.querySelectorAll('input[name="game"]:checked')).map(cb => cb.value);
    const selectedPlayers = Array.from(form.querySelectorAll('input[name="player"]:checked')).map(cb => cb.value);

    const response = await fetch('/get_lineup_data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        games: selectedFiles,
        players: selectedPlayers
      })
    });
    const data = await response.json();
    renderTable(data, tableDiv);
  })
}

function handleShootingFormSubmission(form, figureDiv) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const selectedFiles = Array.from(form.querySelectorAll('input[name="game"]:checked')).map(cb => cb.value);
    const selectedPlayers = Array.from(form.querySelectorAll('input[name="player"]:checked')).map(cb => cb.value);

    const response = await fetch('/get_shooting_fig', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        games: selectedFiles,
        players: selectedPlayers
      })
    });
    console.log("Sending:", {games: selectedFiles, players: selectedPlayers})
    const data = await response.json()
    console.log(data)

    if (data.image) {
      const img = document.createElement('img');
      img.src = `data:image/png;base64,${data.image}`;
      img.alt = "Shooting Chart"
      img.style.maxWidth = "100%";

      figureDiv.innerHTML = ''
      figureDiv.appendChild(img)
    } else {
      figureDiv.innerHTML = `<p style="color:red">Error loading figure</p>`;
    }
  });
}

//Handle Lineup Form Submission
function handleBoxFormSubmission(form, tableDiv) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const selectedFiles = Array.from(form.querySelectorAll('input[name="game"]:checked')).map(cb => cb.value);
    const selectedFormat = form.querySelector('input[name="format"]:checked')?.value;
    const response = await fetch('/get_box_data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        games: selectedFiles,
        format: selectedFormat
      })
    });
    const data = await response.json();
    renderTable(data, tableDiv);
  })
}



//Document implementation
document.addEventListener('DOMContentLoaded', () => {
  console.log("JS Loaded");
  //Tab switching
  handleTabSwitching();

  //Shooting tab
  const shootingForm = document.getElementById('shooting-form');
  const shootingFigureDiv = document.getElementById('shooting-figure');
  handleShootingFormSubmission(shootingForm, shootingFigureDiv);

  const shootingGameDropdownToggle = document.getElementById('shootingGameDropdownToggle');
  const shootingGameDropdown = document.getElementById('shootingGameDropdown');
  const shootingGameSelectAll = document.getElementById('shootingGameSelectAll');
  toggleDropdown(shootingGameDropdownToggle, shootingGameDropdown);
  handleSelectAll(shootingGameSelectAll, shootingGameDropdown);
  closeDropdownOnOutsideClick(shootingGameDropdownToggle, shootingGameDropdown)

  const shootingPlayerDropdownToggle = document.getElementById('shootingPlayerDropdownToggle');
  const shootingPlayerDropdown = document.getElementById('shootingPlayerDropdown');
  toggleDropdown(shootingPlayerDropdownToggle, shootingPlayerDropdown);
  closeDropdownOnOutsideClick(shootingPlayerDropdownToggle, shootingPlayerDropdown)

  //Lineup tab
  const lineupForm = document.getElementById('lineup-form');
  const lineupTableDiv = 'lineup-table';
  handleLineupFormSubmission(lineupForm, lineupTableDiv);

  const lineupGameDropdownToggle = document.getElementById('lineupGameDropdownToggle');
  const lineupGameDropdown = document.getElementById('lineupGameDropdown');
  const lineupGameSelectAll = document.getElementById('lineupGameSelectAll');
  toggleDropdown(lineupGameDropdownToggle, lineupGameDropdown);
  handleSelectAll(lineupGameSelectAll, lineupGameDropdown);
  closeDropdownOnOutsideClick(lineupGameDropdownToggle, lineupGameDropdown)

  const lineupPlayerDropdownToggle = document.getElementById('lineupPlayerDropdownToggle');
  const lineupPlayerDropdown = document.getElementById('lineupPlayerDropdown');
  toggleDropdown(lineupPlayerDropdownToggle, lineupPlayerDropdown);
  closeDropdownOnOutsideClick(lineupPlayerDropdownToggle, lineupPlayerDropdown)

  //Box tab
  const boxForm = document.getElementById('box-form');
  const boxTableDiv = 'box-table';
  handleBoxFormSubmission(boxForm, boxTableDiv);

  const boxGameDropdownToggle = document.getElementById('boxGameDropdownToggle');
  const boxGameDropdown = document.getElementById('boxGameDropdown');
  const boxGameSelectAll = document.getElementById('boxGameSelectAll');
  toggleDropdown(boxGameDropdownToggle, boxGameDropdown);
  handleSelectAll(boxGameSelectAll, boxGameDropdown);
  closeDropdownOnOutsideClick(boxGameDropdownToggle, boxGameDropdown)

  const boxFormatDropdownToggle = document.getElementById('boxFormatDropdownToggle');
  const boxFormatDropdown = document.getElementById('boxFormatDropdown');
  toggleDropdown(boxFormatDropdownToggle, boxFormatDropdown)
  closeDropdownOnOutsideClick(boxFormatDropdownToggle, boxFormatDropdown)


  


})