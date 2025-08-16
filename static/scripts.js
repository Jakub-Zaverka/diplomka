// Used for redirecting user between edit mode and normal sheet due to the need of argument in the url
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".edit-button").forEach(button => {
        button.addEventListener("click", () => {
            const url = button.dataset.url;
            window.location.href = url;
        });
    });
});

// Adding items to Inventory
// function getInventoryData() {
//     const tableRows = document.querySelectorAll('#inventoryModal table tbody tr');
//     const data = [];
//     const url = "/api/inventory";

//     tableRows.forEach(row => {
//         const amountInput = row.querySelector('input[type="text"], input:not([type])'); // množství
//         const nameCell = row.querySelectorAll('td')[0]; // název itemu
//         const checkbox = row.querySelector('input[type="checkbox"]');

//         if (checkbox && checkbox.checked) {
//             const item = {
//                 amount: amountInput?.value?.trim() || '',
//                 UUID: nameCell?.dataset.id
//             };
//             data.push(item);
//         }
//     });

//     fetch(url, {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json"
//         },
//         body: JSON.stringify({ items: data }) // pošle pole položek jako "items"
//     })
//         .then(response => {
//             if (!response.ok) {
//                 throw new Error(`HTTP error! status: ${response.status}`);
//             }
//             return response.json();
//         })
//         .then(result => {
//             console.log("Úspěšně odesláno:", result);
//         })
//         .catch(error => {
//             console.error("Chyba při odesílání dat:", error);
//         });
// }


// Uloží aktuální stav checkboxů (UUID -> true/false)
let lastState = {};

// Uloží aktuální stav všech checkboxů + množství
function saveChanges() {
    lastState = {};
    document.querySelectorAll('#edit-table tbody > tr:not(.collapse)').forEach(row => {
        const uuidCell = row.querySelector("td[data-id]");
        const checkbox = row.querySelector('input[type="checkbox"]');
        const amountInput = row.querySelector('input[type="text"], input:not([type="checkbox"])');

        if (!uuidCell || !checkbox) return;

        const uuid = uuidCell.dataset.id;
        const amount = amountInput?.value?.trim() || '';

        lastState[uuid] = {
            checked: checkbox.checked,
            amount: amount
        };
    });
}

function getChanges() {
    const checked = [];
    const unchecked = [];
    const changed = [];

    document.querySelectorAll('#edit-table tbody > tr:not(.collapse)').forEach(row => {
        const uuidCell = row.querySelector("td[data-id]");
        const checkbox = row.querySelector('input[type="checkbox"]');
        const amountInput = row.querySelector('input[type="text"], input:not([type="checkbox"])');

        if (!uuidCell || !checkbox) return;

        const uuid = uuidCell.dataset.id;
        const amount = amountInput?.value?.trim() || '';

        const previous = lastState[uuid] || { checked: false, amount: '' };
        const currentChecked = checkbox.checked;

        if (!previous.checked && currentChecked) {
            checked.push({ UUID: uuid, amount });
        } else if (previous.checked && !currentChecked) {
            unchecked.push({ UUID: uuid });
        } else if (previous.checked && currentChecked && previous.amount !== amount) {
            changed.push({ UUID: uuid, amount });
        }
    });

    return { checked, unchecked, changed };
}


// Načti výchozí stav při načtení stránky
document.addEventListener("DOMContentLoaded", () => {
    saveChanges();
});



// Finální Volaná Funkce pro Změnu Inventory
// Řeší i aktualizaci bez načtení stránky
// Pokud uživatel zadá něco a pak znovu načte stránku, tak při dalším vstupu uživatel přijde o uložené vstupy
function getInventoryChanges() {
    const changes = getChanges();
    console.log("Added:", changes.checked);
    console.log("Removed:", changes.unchecked);
    console.log("Changed:", changes.changed);

    const url = "/api/inventory";
    fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ changes }) // pošle pole položek jako "items"
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error status: ${response.status}`);
            }
            return response.json();
        })
        .then(result => {
            console.log("Úspěšně odesláno:", result);
        })
        .catch(error => {
            console.error("Chyba při odesílání dat:", error);
        });


    saveChanges(); // uloží aktuální stav jako nový výchozí
}

// TODO: HACKFIX pro opravení špatně pamarujících se čísel?
document.addEventListener('DOMContentLoaded', () => {
    saveChanges()
});




// TODO:Projít dopodrobna tuto funkci
document.addEventListener("DOMContentLoaded", function () {
    const equipBtn = document.getElementById("equip-selected");
    const unequipBtn = document.getElementById("unequip-selected");

    async function processSelection(action) {
        const checkboxes = document.querySelectorAll('.equip-checkbox:checked');

        for (const checkbox of checkboxes) {
            const uuid = checkbox.dataset.uuid;
            const itemBlock = checkbox.closest(`tbody[data-uuid="${uuid}"]`);

            const toTable = document.querySelector(
                action === "equip" ? "#equipped-table" : "#inventory-table"
            );

            const response = await fetch('/api/inventory_equipped', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    change: action,
                    items: { UUID: uuid }
                })
            });

            if (response.ok) {
                toTable.appendChild(itemBlock);

                const newCheckbox = itemBlock.querySelector('.equip-checkbox');
                if (newCheckbox) newCheckbox.checked = false;
            } else {
                alert(`Chyba při aktualizaci položky ${uuid}`);
            }
        }
    }

    equipBtn.addEventListener("click", () => processSelection("equip"));
    unequipBtn.addEventListener("click", () => processSelection("unequip"));
});





// Auto updating stats in the DB,
// TODO: Adapt to other parts of sheet, like name, AC class and so on
document.addEventListener("DOMContentLoaded", function () {
    // vybere úplně všechny elementy s danou class
    document.querySelectorAll(".auto_update_stats").forEach(element => {
        element.addEventListener("change", () => {
            const url = "/api/stats";
            const value = element.value;
            const element_id = element.id || null;

            fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ value: value, id: element_id })
            })
                .then(response => response.json())
                .then(data => {
                    console.log(`Změna ${element.name || element.id} uložena:`, data);
                })
                .catch(error => {
                    console.error(`Chyba při ukládání ${element.name || element.id}:`, error);
                });
        });
    });
});

// Řeší funcionalitu healthbaru a komunikaci s db
// TODO: Upravit ideálně na jedno volání funkce
function updateHealtbar(max) {
    let hp_element = document.getElementById("hp")
    let temp_hp_element = document.getElementById("temp_hp")
    updateFromInput(hp_element)
    updateFromInput(temp_hp_element)

    let current_hp = parseInt(hp_element.value) || 0;
    let temp_hp = parseInt(temp_hp_element.value) || 0;

    let hp_bar = document.getElementById("hp_progress");
    let temp_bar = document.getElementById("hp_progress_overhealth");

    // HP bar
    let hp_percent = (current_hp / max) * 100;
    if (hp_percent > 100) hp_percent = 100;

    // Temp HP bar
    let temp_percent = (temp_hp / max) * 100;
    if (temp_percent > 100) temp_percent = 100;

    hp_bar.style.width = `${hp_percent}%`;
    temp_bar.style.width = `${temp_percent}%`;
}


// univerzální update z inputu a odeslání na univerzální /api/stats endpoint, TODO: použít pro více funkcí
function updateFromInput(input) {
    const url = "/api/stats";
    const value = input.value;
    const input_id = input.id || null;
    fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ value: value, id: input_id })
    })
        .then(response => response.json())
        .then(data => {
            console.log(`Změna ${input.name} uložena:`, data);
        })
        .catch(error => {
            console.error(`Chyba při ukládání ${input.name}:`, error);
        });
};


// Update jedné dovednosti a poslání na endpoint
function updateSkill(id, value) {
    fetch("/api/skills", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            id: id,
            value: parseInt(value)
        })
    })
        .then(resp => resp.json())
        .then(result => {
            if (result.status !== "OK") {
                alert("Chyba při ukládání dovednosti");
            }
        })
        .catch(error => {
            console.error(error);
            alert("Chyba připojení");
        });
}

function deleteChar(button) {
    id = button.id
    tr = document.getElementById(id + "_tr")
    fetch("/api/delete", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            char_id: id,
        })
    })
        .then(resp => resp.json())
        .then(result => {
            if (result.status !== "OK") {
                alert("Chyba při mazání postavy");
            }
            else {
                tr.remove()
            }
        })
        .catch(error => {
            console.error(error);
            alert("Chyba připojení");
        });
}


// Tracking charges jednotlivých features
function charges(input) {
    // id formátu: "<UUID>_<index>"
    const parts = input.id.split("_");
    const baseId = parts[0];
    // -1 kvůli opravě po přidání i+1 do html u ID
    const index = parseInt(parts[1], 10) - 1;

    const container = document.getElementById(baseId + "_div");
    if (!container) return;

    const checkboxes = Array.from(container.querySelectorAll('input[type="checkbox"]'));

    if (!input.checked) {
        // klik na zaškrtnutý → zjisti, jestli za ním jsou další zaškrtnuté
        const hasCheckedAfter = checkboxes.slice(index + 1).some(cb => cb.checked);

        if (hasCheckedAfter) {
            // odklikni všechny za ním
            checkboxes.forEach((cb, i) => {
                if (i > index) cb.checked = false;
            });
            input.checked = true; // kliknutý zůstane zapnutý
        } else {
            // byl poslední → vypni i ten
            input.checked = false;
        }
    } else {
        // klik na nezaškrtnutý → zapni vše do indexu
        checkboxes.forEach((cb, i) => {
            if (i <= index) cb.checked = true;
        });
    }

    console.log(parts[1])
    console.log(!input.checked)
    if (parts[1] == "1" && !input.checked) {
        parts[1] = "0"
    }

    console.log(parts)
    fetch("/api/charges", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            id: parts[0],
            value: parts[1]
        })
    })
        .then(resp => resp.json())
        .then(result => {
            if (result.status !== "OK") {
                alert("Chyba při ukládání dovednosti");
            }
        })
        .catch(error => {
            console.error(error);
            alert("Chyba připojení");
        });
}


// Testing class
// document.addEventListener("DOMContentLoaded", function () {
//     document.querySelectorAll(".post").forEach(button => {
//         button.addEventListener("click", () => {
//             const url = "/api/test";
//             console.log("URL:", url)

//             fetch(url, {
//                 method: "POST",
//                 headers: {
//                     "Content-Type": "application/json"
//                 },
//                 body: JSON.stringify({ message: "Edit request from JS" })
//             })
//                 .then(response => response.json())
//                 .then(data => {
//                     console.log("Odpověď serveru:", data);
//                     // Můžeš tady třeba přesměrovat dál nebo aktualizovat stránku
//                 })
//                 .catch(error => console.error("Chyba při POST požadavku:", error));
//         });
//     });
// });


// Search in table
// TODO:Udělat lepší search napříč všemi polemi - poslední až funguje, protože přepíše ty předcházející
function search_table() {
    // Declare variables
    var input, filter, table, tr, td1, i, txtValue;
    input = document.getElementById("search_input");
    filter = input.value.toUpperCase();
    table = document.getElementById("table");
    tr = table.getElementsByTagName("tr");

    // Loop through all table rows, and hide those who don't match the search query
    for (i = 0; i < tr.length; i++) {
        td1 = tr[i].getElementsByTagName("td")[0];
        td2 = tr[i].getElementsByTagName("td")[2];

        // Jestli je ve druhém sloupci něco
        if (td2) {
            txtValue = (td2.textContent || td2.innerText);
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }
        // Jesli je v prvním sloupci něco
        if (td1) {
            txtValue = (td1.textContent || td1.innerText);
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }
    }
}









