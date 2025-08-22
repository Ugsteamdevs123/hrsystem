document.addEventListener("DOMContentLoaded", function () {
  const modelSelect = document.getElementById("id_model_name");
  const fieldSelect = document.getElementById("id_field_name");
  const displayName = document.getElementById("id_display_name");
  const pathInput = document.getElementById("id_path");

  if (!modelSelect || !fieldSelect) return;

  function prettyLabel(s) {
    return s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  }

  function setOptions(selectEl, options) {
    selectEl.innerHTML = "";
    options.forEach(([value, label]) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      selectEl.appendChild(opt);
    });
  }

  function loadFields(modelName) {
    setOptions(fieldSelect, [["", "Loading…"]]);
    // ✅ Change APP_LABEL_FOR_ADMIN below to your admin app label used in URLs
    fetch(`/admin/user/fieldreference/get-fields/?model=${encodeURIComponent(modelName)}`)
      .then(r => r.json())
      .then(data => {
        const opts = [["", "Select a field…"], ...data];
        setOptions(fieldSelect, opts);
      });
  }

  modelSelect.addEventListener("change", function () {
    const modelName = this.value;
    if (!modelName) {
      setOptions(fieldSelect, [["", "Select a model first…"]]);
      if (displayName) displayName.value = "";
      if (pathInput) pathInput.value = "";
      return;
    }
    loadFields(modelName);
  });

  fieldSelect.addEventListener("change", function () {
    const modelName = modelSelect.value;
    const fieldName = this.value;

    if (displayName) {
      displayName.value = fieldName ? prettyLabel(fieldName) : "";
    }
    if (pathInput) {
      pathInput.value = (modelName && fieldName)
        ? `employee__${modelName.toLowerCase()}__${fieldName}`
        : "";
    }
  });
});
