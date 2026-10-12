// Small quality-of-life script for the admin: add/remove contact-link rows.

document.addEventListener("click", (event) => {
  const addButton = event.target.closest("#add-link");
  const removeButton = event.target.closest(".remove-row");

  if (addButton) {
    const rows = document.getElementById("link-rows");
    const row = document.createElement("div");
    row.className = "link-row";
    row.innerHTML = `
      <input type="text" name="link_label" placeholder="Website">
      <input type="url" name="link_url" placeholder="https://…">
      <button type="button" class="remove-row" title="Remove">×</button>`;
    rows.appendChild(row);
    row.querySelector("input").focus();
  }

  if (removeButton) {
    removeButton.closest(".link-row").remove();
  }
});
