function todayISO() {
    return new Date().toISOString().slice(0, 10);
}

document.addEventListener('DOMContentLoaded', function() {
    var el = document.getElementById(fetchDateId);
    if (el && !el.value) el.value = todayISO();
    el.addEventListener("change", (e)=>{e.target.closest("form").submit()});

    document.querySelectorAll("#deleteDate").forEach(elm => {
      elm.value = el.value;
    });

    document.querySelectorAll("#downloadDate").forEach(elm => {
      elm.value = el.value;
    });


  });

const table = document.getElementById("dataTable");

const EDITABLE_COLUMNS = new Set(["amount", "receipts", ""]);

if (table){
table.addEventListener("click", (e) => {
  if (typeof isAdmin !== 'undefined' && !isAdmin) return;
  
  const td = e.target.closest("td");
  if (!td) return;

  const column = td.dataset.column;
  if (!column) return;

  if (td.dataset.readonly === "true") return;

  if (!EDITABLE_COLUMNS.has(column)) return;
  if (td.classList.contains("editing")) return;

  makeEditable(td, column);
});
}

function makeEditable(td, column) {
  const oldValue = td.textContent.trim();
  td.classList.add("editing");
  td.textContent = "";

  const input = document.createElement("input");

  input.value = oldValue;
  input.className = "form-control soft-input input-sm";
  input.style.width = "100%";

  td.appendChild(input);
  input.focus();
  input.select();

  function commit() {
    td.textContent = input.value.trim();
    td.classList.remove("editing");
  }

  function cancel() {
    td.textContent = oldValue;
    td.classList.remove("editing");
  }

  input.addEventListener("blur", commit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") commit();
    if (e.key === "Escape") cancel();
  });
}

function extractTableData() {
  const table = document.getElementById("dataTable");
  const data = [];

  table.querySelectorAll("tbody tr").forEach(tr => {
    const row = {};

    tr.querySelectorAll("td[data-column]").forEach(td => {
      row[td.dataset.column] = td.textContent.trim();
    });

    id = tr.querySelector("input[id=row-id]")
    if (id){
      row["id"] = tr.querySelector("input[id=row-id]").value;
    }
    data.push(row);
  });

  return data;
}

if (table){
document.getElementById("SubmitData").addEventListener("click", (e) => {
  e.preventDefault();

  const tableData = extractTableData();
  document.getElementById("rowData").value = JSON.stringify(tableData);

  e.target.closest("form").submit();
});
}