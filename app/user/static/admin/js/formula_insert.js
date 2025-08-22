document.addEventListener("DOMContentLoaded", function () {
    console.log("hiiii");
  const insertFieldSelect = document.getElementById("id_insert_field"); // dropdown
  const formulaInput = document.getElementById("id_formula"); // textarea or input for formula

  if (!insertFieldSelect || !formulaInput) return;

  insertFieldSelect.addEventListener("change", function () {
    const fieldValue = this.value;
    if (!fieldValue) return;

    // Insert at cursor position in textarea/input
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    const current = formulaInput.value;

    formulaInput.value =
      current.substring(0, start) + fieldValue + current.substring(end);

    // Move cursor after inserted text
    formulaInput.selectionStart = formulaInput.selectionEnd =
      start + fieldValue.length;

    // reset dropdown to placeholder
    this.value = "";
    formulaInput.focus();
  });
});
