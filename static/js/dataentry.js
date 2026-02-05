const typeSelect = document.getElementById("type-select");
const subtypeSelect = document.getElementById("subtype-select");

window.addEventListener("load", handleChange);

let tableInitialized = false;
let isClearing = false;

let currentCols = [];
let currentColumnCount = 0;

let fillingDate = "";

let tableData = {
  headings: [],
  data: []
};

/* ------------------ CUSTOM AUTOCOMPLETE ------------------ */

let activeDropdown = null;

function setupAutocomplete(input) {
  if (typeof clientNames === "undefined" || clientNames.length === 0) return;

  const wrapper = document.createElement("div");
  wrapper.className = "autocomplete-wrapper";
  input.parentNode.insertBefore(wrapper, input);
  wrapper.appendChild(input);

  const dropdown = document.createElement("div");
  dropdown.className = "autocomplete-dropdown";
  wrapper.appendChild(dropdown);

  let selectedIndex = -1;

  input.addEventListener("input", () => {
    const val = input.value.toLowerCase();
    dropdown.innerHTML = "";
    selectedIndex = -1;

    if (!val) {
      dropdown.classList.remove("show");
      return;
    }

    const matches = clientNames.filter(name => 
      name.toLowerCase().includes(val)
    ).slice(0, 10);

    if (matches.length === 0) {
      dropdown.classList.remove("show");
      return;
    }

    matches.forEach((name, idx) => {
      const item = document.createElement("div");
      item.className = "autocomplete-item";
      item.textContent = name;
      item.addEventListener("click", () => {
        input.value = name;
        dropdown.classList.remove("show");
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
      item.addEventListener("mouseenter", () => {
        selectedIndex = idx;
        updateSelection(dropdown, selectedIndex);
      });
      dropdown.appendChild(item);
    });

    const rect = input.getBoundingClientRect();
    dropdown.style.top = (rect.bottom + 4) + "px";
    dropdown.style.left = rect.left + "px";
    dropdown.style.width = Math.max(rect.width, 300) + "px";

    dropdown.classList.add("show");
    activeDropdown = dropdown;
  });

  input.addEventListener("keydown", (e) => {
    const items = dropdown.querySelectorAll(".autocomplete-item");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
      updateSelection(dropdown, selectedIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
      updateSelection(dropdown, selectedIndex);
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      input.value = items[selectedIndex].textContent;
      dropdown.classList.remove("show");
    } else if (e.key === "Escape") {
      dropdown.classList.remove("show");
    }
  });

  input.addEventListener("blur", () => {
    setTimeout(() => dropdown.classList.remove("show"), 150);
  });
}

function updateSelection(dropdown, index) {
  dropdown.querySelectorAll(".autocomplete-item").forEach((item, i) => {
    item.classList.toggle("selected", i === index);
  });
}

document.addEventListener("click", (e) => {
  if (activeDropdown && !e.target.closest(".autocomplete-wrapper")) {
    activeDropdown.classList.remove("show");
  }
});

/* ------------------ HELPERS ------------------ */

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function getDefaultDate() {
  return fillingDate || todayISO();
}

/* ------------------ STATE SYNC ------------------ */

function updatetableData() {
  const table = document.getElementById("dataEntryTable");
  if (!table || !table.tBodies.length) return;

  const rows = [];
  table.tBodies[0].querySelectorAll("tr").forEach(row => {
    rows.push(
      [...row.querySelectorAll("td")]
        .slice(0, currentColumnCount) // ignore Action column
        .map(td => td.querySelector("input").value)
    );
  });

  tableData.data = rows;
}

/* ------------------ SCHEMA REMAP ------------------ */

function remapRowsByColumnName(oldCols, newCols, oldData) {
  const oldIndexMap = {};
  oldCols.forEach((col, i) => (oldIndexMap[col.name] = i));

  return oldData.map(oldRow =>
    newCols.map(col => {
      const oldIndex = oldIndexMap[col.name];
      if (oldIndex !== undefined) return oldRow[oldIndex] ?? "";
      return col.type === "date" ? todayISO() : "";
    })
  );
}

/* ------------------ MAIN HANDLER ------------------ */

function handleChange() {
  if (!typeSelect.value || !subtypeSelect.value) return;

  const cols = columns[typeSelect.value][subtypeSelect.value];

  if (tableInitialized && !isClearing) {
    updatetableData();
    tableData.data = remapRowsByColumnName(
      tableData.headings,
      cols,
      tableData.data
    );
  }

  currentCols = cols;
  currentColumnCount = cols.length;
  tableData.headings = cols;

  if (!tableInitialized) {
    tableInitialized = true;

    tableData.data = [
      cols.map(col => (col.type === "date" ? getDefaultDate() : ""))
    ];

    const container = document.getElementById("main");

    const tableWrapper = document.createElement("div");
    tableWrapper.className = "table-responsive mt-4";

    const table = document.createElement("table");
    table.id = "dataEntryTable";
    table.className =
      "table table-borderless align-middle mb-0 custom-table";
    table.addEventListener("input", updatetableData);

    table.appendChild(document.createElement("thead"));
    table.appendChild(document.createElement("tbody"));

    tableWrapper.appendChild(table);
    container.appendChild(tableWrapper);

    const actions = document.createElement("div");
    actions.className = "table-actions mt-3";

    actions.append(
      makeButton("Add Row", addButtonClick),
      makeButton("Submit Table", submitButtonClick),
      makeButton("Clear Table", clearButtonClick)
    );

    container.appendChild(actions);
  }

  renderHeader();
  renderBody();
  isClearing = false;
}

/* ------------------ RENDER ------------------ */

function renderHeader() {
  const table = document.getElementById("dataEntryTable");
  const thead = table.tHead;
  thead.replaceChildren();

  const tr = document.createElement("tr");

  currentCols.forEach(col => {
    const th = document.createElement("th");
    th.textContent = col.name;
    th.className = "text-muted fw-semibold px-4 py-3";
    tr.appendChild(th);
  });

  const actionTh = document.createElement("th");
  actionTh.className = "text-muted fw-semibold px-4 py-3";
  actionTh.textContent = "Action";
  tr.appendChild(actionTh);

  thead.appendChild(tr);
}

function renderBody() {
  const table = document.getElementById("dataEntryTable");
  const tbody = table.tBodies[0];
  tbody.replaceChildren();

  tableData.data.forEach((row, rowIndex) => {
    const tr = document.createElement("tr");

    currentCols.forEach((col, colIndex) => {
      const td = document.createElement("td");
      td.className = "px-4 py-3";

      const input = document.createElement("input");
      input.type = col.type || "text";
      input.className = "form-control soft-input input-sm";
      input.value =
        row[colIndex] ??
        (input.type === "date" ? getDefaultDate() : "");

      if (col.type === "date") {
        input.addEventListener("change", (e) => {
          fillingDate = e.target.value;
        });
      }

      td.appendChild(input);
      tr.appendChild(td);

      if (col.name.toLowerCase() === "receipts") {
        input.setAttribute("autocomplete", "off");
        setTimeout(() => setupAutocomplete(input), 0);
      }
    });

    const actionTd = document.createElement("td");
    actionTd.className = "text-center align-middle";
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-sm btn-danger";
    removeBtn.textContent = "✕";
    removeBtn.onclick = () => removeRow(rowIndex);

    actionTd.appendChild(removeBtn);
    tr.appendChild(actionTd);

    tbody.appendChild(tr);
  });
}

/* ------------------ VALIDATION ------------------ */

function validateTableData() {
  updatetableData();

  let isValid = true;
  const errors = [];

  const table = document.getElementById("dataEntryTable");

  table.tBodies[0].querySelectorAll("tr").forEach((row, r) => {
    row.querySelectorAll("input").forEach((input, c) => {
      input.classList.remove("is-invalid");
      const value = input.value.trim();
      const col = currentCols[c];

      if (!value) {
        isValid = false;
        input.classList.add("is-invalid");
        errors.push(`Row ${r + 1}: ${col.name} is required`);
        return;
      }

      if (col.type === "number") {
        const num = Number(value);
        if (Number.isNaN(num) || num <= 0) {
          isValid = false;
          input.classList.add("is-invalid");
          errors.push(`Row ${r + 1}: ${col.name} must be a positive number`);
        }
      }

      if (col.type === "date") {
        const date = new Date(value);
        if (isNaN(date.getTime())) {
          isValid = false;
          input.classList.add("is-invalid");
          errors.push(`Row ${r + 1}: ${col.name} must be a valid date`);
        }
      }
    });
  });

  if (!isValid) {
    alert("Please fix these errors:\n\n" + errors.join("\n"));
  }

  return isValid;
}

/* ------------------ ACTIONS ------------------ */

function addButtonClick() {
  updatetableData();

  tableData.data.push(
    currentCols.map(col => (col.type === "date" ? getDefaultDate() : ""))
  );

  renderBody();
}

function removeRow(index) {
  if (tableData.data.length === 1) {
    alert("At least one row is required.");
    return;
  }

  tableData.data.splice(index, 1);
  renderBody();
}

function clearButtonClick() {
  isClearing = true;
  fillingDate = "";
  tableData.data = [
    currentCols.map(col => (col.type === "date" ? todayISO() : ""))
  ];
  renderBody();
  isClearing = false;
}

function submitButtonClick() {
  if (!validateTableData()) return;

  const rowData = document.getElementById("rowData");
  rowData.value = JSON.stringify(tableData);
  document.getElementById("dataentryform").submit();
}

/* ------------------ BUTTON HELPER ------------------ */

function makeButton(label, handler) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-purple me-2";
  btn.textContent = label;
  btn.onclick = handler;
  return btn;
}

/* ------------------ EVENTS ------------------ */

typeSelect.addEventListener("change", handleChange);
subtypeSelect.addEventListener("change", handleChange);
