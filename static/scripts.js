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


// Řeší aktualizaci inventáře bez načtení stránky
function refreshInventory(result) {
    const equippedTable = document.getElementById("equipped-table");
    const inventoryTable = document.getElementById("inventory-table");

    // smažeme staré položky, ale necháme první řádek s tlačítkem "Edit Inventory"
    equippedTable.querySelectorAll("tbody").forEach(tbody => tbody.remove());
    inventoryTable.querySelectorAll("tbody").forEach((tbody, i) => {
        if (i > 0) tbody.remove();
    });

    // znovu projdeme položky z backendu
    result.inventory.forEach(item => {
        const tbody = document.createElement("tbody");
        tbody.setAttribute("data-uuid", item.UUID);

        tbody.innerHTML = `
            <tr>
                <td>
                    <input class="form-check-input equip-checkbox" type="checkbox" data-uuid="${item.UUID}">
                </td>
                <td>
                    <p class="mb-0">${item.count}</p>
                </td>
                <td data-id="${item.UUID}" class="item-name">${item.name}</td>
                <td class="text-end">
                    <button class="btn btn-primary m-1" type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#Collapse${item.UUID}"
                        data-damage="${item.damage}"
                        data-modifier="${item.damage_modifier}"
                        aria-expanded="false"
                        aria-controls="Collapse${item.UUID}">
                        Info
                    </button>
                </td>
            </tr>
            <tr>
                <td colspan="4" class="collapse" id="Collapse${item.UUID}">
                    ${item.description}
                </td>
            </tr>
        `;

        if (item.equipped == 1) {
            equippedTable.appendChild(tbody);
        } else {
            inventoryTable.appendChild(tbody);
        }
    });
}


// Finální Volaná Funkce pro Změnu Inventory

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

            if (result.status === "OK") {
                refreshInventory(result)
            }
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




// Spells
// Uloží stav spells zvlášť od inventáře
let lastSpellState = {};

document.addEventListener("DOMContentLoaded", () => {
    saveSpellChanges();
});

function saveSpellChanges() {
    lastSpellState = {};
    document.querySelectorAll('#spell-edit-table tbody > tr:not(.collapse)').forEach(row => {
        const uuidCell = row.querySelector("td[data-id]");
        const checkbox = row.querySelector('input[type="checkbox"]');
        const amountInput = row.querySelector('input[type="text"], input:not([type="checkbox"])');

        if (!uuidCell || !checkbox) return;

        const uuid = uuidCell.dataset.id;
        const amount = amountInput?.value?.trim() || '';

        lastSpellState[uuid] = {
            checked: checkbox.checked,
            amount: amount
        };
    });
}

function getSpellChanges() {
    const checked = [];
    const unchecked = [];
    const changed = [];

    document.querySelectorAll('#spell-edit-table tbody > tr:not(.collapse)').forEach(row => {
        const uuidCell = row.querySelector("td[data-id]");
        const checkbox = row.querySelector('input[type="checkbox"]');
        const amountInput = row.querySelector('input[type="text"], input:not([type="checkbox"])');

        if (!uuidCell || !checkbox) return;

        const uuid = uuidCell.dataset.id;
        const amount = amountInput?.value?.trim() || '';

        const previous = lastSpellState[uuid] || { checked: false, amount: '' };
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

function sendSpellChanges() {
    const changes = getSpellChanges();
    console.log("Added Spells:", changes.checked);
    console.log("Removed Spells:", changes.unchecked);
    console.log("Changed Spells:", changes.changed);

    const url = "/api/spells";
    fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ changes })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error status: ${response.status}`);
            }
            return response.json();
        })
        .then(result => {
            console.log("Úspěšně odesláno (Spells):", result);

            if (result.status === "OK") {
                refreshSpells(result);
            }
        })
        .catch(error => {
            console.error("Chyba při odesílání dat (Spells):", error);
        });

    saveSpellChanges(); // uloží aktuální stav jako nový výchozí
}

// Refresh spell tabulky
function refreshSpells(result) {
    const spellTable = document.querySelector("#nav-spells table tbody");
    if (!spellTable) return; // bezpečnostní pojistka

    // smažeme všechny řádky
    spellTable.querySelectorAll("tr").forEach(row => row.remove());

    // přidáme kouzla z backendu
    result.spells.forEach(spell => {
        spellTable.insertAdjacentHTML("beforeend", `
            <tr>
                <td>${spell.level}</td>
                <td>${spell.name}</td>
                <td>${spell.range}</td>
                <td>${spell.damage || ""} ${spell.damage_type || ""}</td>
                <td>
                    <button class="btn btn-primary m-1" type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#Collapse${spell.UUID}"
                        aria-expanded="false"
                        aria-controls="Collapse${spell.UUID}">
                        C
                    </button>
                </td>
            </tr>
            <tr>
                <td colspan="5" class="collapse" id="Collapse${spell.UUID}">
                    ${spell.description || ""}
                    ${spell.components || ""}
                    ${spell.duration || ""}
                </td>
            </tr>
        `);
    });

    // nakonec tlačítko Edit Spells
    spellTable.insertAdjacentHTML("beforeend", `
        <tr>
            <td colspan="5" class="text-center">
                <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#spellModal">
                    Edit Spells
                </button>
            </td>
        </tr>
    `);
}

// javascript nemá normální Random funkci
function generateRandomInteger(min, max) {
    return Math.floor(min + Math.random()*(max - min + 1))
}
// Dice Roll - old and not used
function randomRoll(number,die=20,modifier = 0){
    rand = generateRandomInteger(number,die)
    modInt = parseInt(modifier)
    sum = rand+modInt
    return sum
}

//Dice Roll From String
//4d4+1d6+1
function stringDiceRoll(string){
    resultRolls = []
    plusSplit = string.split("+")
    for(let i = 0; i < plusSplit.length; i++){
        dSplit = plusSplit[i].split("d")
        console.log(dSplit)
        if(dSplit.length == 1){
            resultRolls.push(parseInt(dSplit[0]))
        }
        else if(dSplit.length == 2){
            for(let i = 0; i < dSplit[0]; i++){
                resultRolls.push(generateRandomInteger(1,dSplit[1]))
            }
        }
        else{
            console.log("error")
        }
    }
    console.log(resultRolls)
    result = 0
    for(let i = 0; i < resultRolls.length; i++){
        result += resultRolls[i]
    }
    console.log(result)
    return result
}

// Toast funkce pro Dice Rolls
function showToast(element, title = 'Heading') {
            const toastContainer = document.getElementById('toastContainer');
            modifier = element.getAttribute('data-modifier')
            // vytvoření toastu
            const toastEl = document.createElement('div');
            toastEl.className = 'toast align-items-center';
            toastEl.role = 'alert';
            toastEl.ariaLive = 'assertive';
            toastEl.ariaAtomic = 'true';
            toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            
            Random Roll: ${stringDiceRoll('1d20+'+modifier)} (1d20+${modifier})
        </div>
        `;

            toastContainer.appendChild(toastEl);

            // inicializace a zobrazení
            const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastEl);
            toastBootstrap.show();
        }



