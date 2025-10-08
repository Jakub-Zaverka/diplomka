//------------------------------------
// Edit mode
//------------------------------------

// Used for redirecting user between edit mode and normal sheet due to the need of argument in the url
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".edit-button").forEach(button => {
        button.addEventListener("click", () => {
            const url = button.dataset.url;
            window.location.href = url;
        });
    });
});



//------------------------------------
// Inventory
//------------------------------------

// Uloží aktuální stav checkboxů (UUID -> true/false)
let lastState = {};

// Uloží aktuální stav všech checkboxů + množství, aby bylo možné předejít posílání duplikátů napříč znovunačtením stránky
function saveChanges() {
    lastState = {};
    //vybere všechny tr v edit-table, které nemají .collapse
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

    // smaže staré položky, ale nechá první řádek s tlačítkem "Edit Inventory"
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
                <td data-id="${item.UUID}" ${item.damage ? `data-damage="${item.damage}" data-modifier="${item.bonus}"` : ""} class="item-name clickable-div"
                    onclick="showToast(this,'Dice Roll ${item.name}')">
                    ${item.name}
                </td>
                <td class="text-end">
                    <button class="btn btn-primary m-1" type="button"
                        data-bs-toggle="collapse"
                        data-bs-target="#Collapse${item.UUID}"
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




//------------------------------------
// Auto updating stats, AC, a prakticky cokoliv, kam lze dát class .auto_update_stats do DB
//------------------------------------

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

//------------------------------------
// Řeší funcionalitu healthbaru a komunikaci s db
//------------------------------------

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


//------------------------------------
// univerzální update z inputu a odeslání na univerzální /api/stats endpoint, TODO: použít pro více funkcí
//------------------------------------

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

//------------------------------------
// Update jedné dovednosti a poslání na endpoint
//------------------------------------

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
//------------------------------------
// Delete Character
//------------------------------------

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





//------------------------------------
// Search in table
//------------------------------------

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



//------------------------------------
// Spells - funguje obdobně jako inventory
//------------------------------------

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

    // smaže všechny řádky
    spellTable.querySelectorAll("tr").forEach(row => row.remove());

    // přidá kouzla z backendu
    result.spells.forEach(spell => {
        spellTable.insertAdjacentHTML("beforeend", `
            <tr>
                <td>${spell.level}</td>
                <td>${spell.name}</td>
                <td>${spell.range}</td>
                <td data-damage=${spell.damage} onclick="showToast(this,'Dice Roll ${spell.name}')">${spell.damage || ""} ${spell.damage_type || ""}</td>
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


//------------------------------------
// Dice Rolls
//------------------------------------

// javascript nemá normální Random funkci, takže jsem si ji vytvořil
function generateRandomInteger(min, max) {
    return Math.floor(min + Math.random() * (max - min + 1))
}



//Dice Roll From String
//4d4+1d6+1
function stringDiceRoll(string) {
    resultRolls = []
    plusSplit = string.split("+")
    for (let i = 0; i < plusSplit.length; i++) {
        dSplit = plusSplit[i].split("d")
        console.log(dSplit)
        if (dSplit.length == 1) {
            resultRolls.push(parseInt(dSplit[0]))
        }
        else if (dSplit.length == 2) {
            for (let i = 0; i < dSplit[0]; i++) {
                resultRolls.push(generateRandomInteger(1, dSplit[1]))
            }
        }
        else {
            console.log("error")
        }
    }
    console.log(resultRolls)
    result = 0
    for (let i = 0; i < resultRolls.length; i++) {
        result += resultRolls[i]
    }
    console.log(result)
    return result
}

// Toast funkce pro Dice Rolls
function showToast(element = null, title = 'Heading') {
    const toastContainer = document.getElementById('toastContainer');


    // Defaultní hodnoty
    let modifier = "0";
    let dice = "1d20";

    // Pokud máme element, načteme atributy
    if (element) {
        modifier = element.getAttribute('data-modifier') || '0';
        dice = element.getAttribute('data-damage') || '1d20';
    }

    // vytvoření toastu
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center';
    toastEl.role = 'alert';
    toastEl.ariaLive = 'assertive';
    toastEl.ariaAtomic = 'true';

    if (element && element.getAttribute('data-damage')) {
        // Damage roll
        toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            Attack Roll: ${modifier == "0"
                ? `${stringDiceRoll('1d20')} (1d20)`
                // : `${stringDiceRoll('1d20' + '+' + modifier)} (1d20+${modifier})`
                :(modifier < 0 
                    ? `${stringDiceRoll('1d20' + '+' + modifier)} (1d20${modifier})`
                    : `${stringDiceRoll('1d20' + '+' + modifier)} (1d20+${modifier})`)
            }<br>
            Damage Roll: ${modifier == "0"
                ? `${stringDiceRoll(dice)} (${dice})`
                : `${stringDiceRoll(dice + '+' + modifier)} (${dice}+${modifier})`}
        </div>
        `;
    } else {
        // Random roll nebo fallback, když není element
        toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            Random Roll: ${modifier == "0"
                ? `${stringDiceRoll('1d20')} (1d20)`
                // : `${stringDiceRoll('1d20' + '+' + modifier)} (1d20+${modifier})`
                :(modifier < 0 
                    ? `${stringDiceRoll('1d20' + '+' + modifier)} (1d20${modifier})`
                    : `${stringDiceRoll('1d20' + '+' + modifier)} (1d20+${modifier})`)
            }
        </div>
        `;
    }

    toastContainer.appendChild(toastEl);

    // inicializace a zobrazení
    const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastEl);
    toastBootstrap.show();
}


//------------------------------------
// Form Validation
//------------------------------------

function validateForm() {
    let username = document.forms["login-form"]["uname"];
    if (x == "") {
        alert("Name must be filled out");
        return false;
    }
}

// function showPassword(btn) {
//     const wrapper = btn.closest(".input-group");
//     const input = wrapper.querySelector("input");
//     input.type = input.type === "password" ? "text" : "password";
// }

function showPassword(btn) {
    const wrapper = btn.closest(".input-group");
    const input = wrapper.querySelector("input");
    const svg = btn.querySelector("svg");

    // přepni typ inputu
    input.type = input.type === "password" ? "text" : "password";

    // přepni ikonu
    if (svg.classList.contains("bi-eye-fill")) {
        svg.classList.replace("bi-eye-fill", "bi-eye-slash-fill");
        svg.innerHTML = `
          <path d="m10.79 12.912-1.614-1.615a3.5 3.5 0 0 1-4.474-4.474l-2.06-2.06C.938 6.278 0 8 0 8s3 5.5 8 5.5a7 7 0 0 0 2.79-.588M5.21 3.088A7 7 0 0 1 8 2.5c5 0 8 5.5 8 5.5s-.939 1.721-2.641 3.238l-2.062-2.062a3.5 3.5 0 0 0-4.474-4.474z"/>
          <path d="M5.525 7.646a2.5 2.5 0 0 0 2.829 2.829zm4.95.708-2.829-2.83a2.5 2.5 0 0 1 2.829 2.829zm3.171 6-12-12 .708-.708 12 12z"/>`;
    } else {
        svg.classList.replace("bi-eye-slash-fill", "bi-eye-fill");
        svg.innerHTML = `
          <path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0"/>
          <path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8m8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7"/>`;
    }
}


//------------------------------------
// Feature charges tracking
//------------------------------------

// nastaví UI podle nextCount
function applyCharges(container, nextCount) {
    const checkboxes = Array.from(container.querySelectorAll('input[type="checkbox"]'));
    checkboxes.forEach((cb, i) => { cb.checked = i < nextCount; });

    // Najdi tlačítko v parent containeru a disable, pokud není charge
    const button = container.querySelector("button");
    if (button) {
        button.disabled = nextCount === 0;
    }

    return nextCount;
}

// pošli na backend
function postCharges(baseId, nextCount) {
    return fetch("/api/charges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: baseId, value: nextCount }) // číslo, ne string
    });
}

// ruční klik na checkbox
function charges(input) {
    const [baseId, idx1] = input.id.split("_");
    const container = document.getElementById(baseId + "_div");
    if (!container) return;

    const index = parseInt(idx1, 10) - 1;
    const nextCount = input.checked ? (index + 1) : index;

    applyCharges(container, nextCount);

    postCharges(baseId, nextCount)
        .then(r => r.json())
        .then(result => {
            if (result.status !== "OK") alert("Chyba při ukládání dovednosti");
        })
        .catch(err => {
            console.error(err);
            alert("Chyba připojení");
        });
}

// Odebrání 1 charge přes tlačítko "UseAbility"
function useFeature(button) {

    const parent = button.parentNode;
    const checkboxes = parent.querySelectorAll('input[type="checkbox"]');
    if (!checkboxes.length) return;

    // ID checkboxes jsou psané ve tvaru UUID feature_číslo
    const baseId = checkboxes[0].id.split("_")[0];
    const container = document.getElementById(baseId + "_div");

    const remaining = Array.from(checkboxes).filter(checkbox => checkbox.checked).length;
    const nextCount = Math.max(0, remaining - 1);


    applyCharges(container, nextCount);

    postCharges(baseId, nextCount)
        .then(r => r.json())
        .then(result => {
            if (result.status !== "OK") alert("Chyba při ukládání dovednosti");
        })
        .catch(err => {
            console.error(err);
            alert("Chyba připojení");
        });
}



// Feats
function postFeat(selectElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const featId = selectedOption.value;   // UUID featu
    const level = parseInt(selectElement.dataset.level) || 0; // level z atributu data-level

    fetch("/api/feats", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id: featId,
            level: level
        })
    })
        .then(r => r.json())
        .then(data => console.log("Feat uložen:", data))
        .catch(err => console.error("Chyba při ukládání featu:", err));
}

// Class Choices
function postClassChoice(selectElement) {
    // const selectedOption = selectElement.options[selectElement.selectedIndex];
    // //const choice_id = selectedOption.dataset.uuid || 0;   // UUID choice
    // const choice_id = selectedOption.parentNode.dataset.uuid || 0;
    // const choice = selectedOption.value || 0;
    // const level = parseInt(selectedOption.dataset.level) || 0; // level z atributu data-level - zde failne, protože tady neni zatím dořešen TODO:FIX

    const selectedOption = selectElement.options[selectElement.selectedIndex];

    const choice_id = selectElement.dataset.uuid || 0;   // vezme data-uuid přímo ze selectu
    const choice = selectedOption.value || 0;
    const level = parseInt(selectElement.dataset.level) || 0;

    console.log(choice_id)
    console.log(choice)
    console.log(level)



    fetch("/api/character_choice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id: choice_id,
            choice: choice,
            level: level
        })
    })
        .then(r => r.json())
        .then(data => console.log("Feat uložen:", data))
        .catch(err => console.error("Chyba při ukládání featu:", err));
}


//-----------------------
// AI Assistent
//-----------------------
$(document).ready(function () {
    function addMessage(text, sender) {
        let html = '';
        if (sender === 'user') {
            html = `
    <div class="d-flex justify-content-end mb-2">
    <div class="d-flex flex-column align-items-end">
        <img src="https://i.imgur.com/HpF4BFG.jpg" width="30" class="rounded-circle mb-1" />
        <span class="fw-bold mb-1">You</span>
        <div class="bg-primary text-white rounded p-2" style="max-width: 75%; word-wrap: break-word;">
            ${text}
        </div>
    </div>
</div>`;
        } else {
            html = `
    <div class="d-flex justify-content-start mb-2">
        <div>
            <span class="d-block mb-1 fw-bold">AI</span>
            <div class="bg-secondary text-dark rounded p-2" style="max-width: 75%; word-wrap: break-word;">
                ${text}
            </div>
        </div>
    </div>`;
        }

        $('#nav-ai #chat-box').append(html);
        $('#nav-ai #chat-box').scrollTop($('#nav-ai #chat-box')[0].scrollHeight);
    }

    function sendMessage() {
        let message = $('#nav-ai #user-input').val().trim();
        if (message === '') return;

        addMessage(message, 'user');
        $('#nav-ai #user-input').val('');

        $.ajax({
            url: "/send_message",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({ message: message }),
            success: function (data) {
                addMessage(data.reply, 'ai');

                // pokud přijde instrukce pro frontend
                if (data.frontend_action) {
                    if (data.frontend_action.type === "show_toast") {
                        const action = data.frontend_action;
                        // showToast(null, action.title);
                        console.log("Toast triggered:", action);
                        console.log(action['total'])
                        // vytvoření toastu
                        const toastEl = document.createElement('div');
                        toastEl.className = 'toast align-items-center';
                        toastEl.role = 'alert';
                        toastEl.ariaLive = 'assertive';
                        toastEl.ariaAtomic = 'true';
                        toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">AI Roll</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            Roll: ${action['total']} ${`(${action['dice']})`}
        </div>
        `;
                        toastContainer.appendChild(toastEl);

                        // inicializace a zobrazení
                        const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastEl);
                        toastBootstrap.show();

                    }
                }
            },
            error: function () {
                addMessage("Error contacting AI.", 'ai');
            }
        });
    }


    // kliknutí na šipku
    $('#nav-ai #send-btn').click(sendMessage);

    // Enter v inputu
    $('#nav-ai #user-input').keypress(function (e) {
        if (e.which === 13) {
            e.preventDefault(); // aby se neodeslal formulář/tab
            sendMessage();
        }
    });

});

//------------------------------
// Změna hesla,emailu a username
//------------------------------

function changeUserInfo(data, password, type) {
    fetch("/api/user_info", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            data: data,
            password: password,
            type: type
        })
    })
        .then(resp => resp.json())
        .then(result => {
            if (result.status !== "OK") {
                // chyba -> zobrazit alert v příslušném modal
                showError(type, result.status);
                return;
            }

            // schovat error, zavřít modal, aktualizovat input
            hideError(type);

            const modalEl = document.getElementById('Modal' + capitalize(type));
            const modal = bootstrap.Modal.getInstance(modalEl);
            modal.hide();

            if (type === "email") {
                document.getElementById("emailInput").value = result.received.data;
            }
            if (type === "username") {
                document.getElementById("usernameInput").value = result.received.data;
                document.getElementById("navBarUsername").textContent = result.received.data;
            }
            // password nepotřebuje update na stránce
        })
        .catch(err => {
            console.error("Chyba:", err);
        });
}
//Existuje jen kvůli naming konvenci v JS a potřebě převést jména modálů na CammelCase
function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function passwordCheck() {
    const newElement = document.getElementById("newPass").value;
    const repeatElement = document.getElementById("repeatPass").value;
    const pass = document.getElementById("pass_password").value;

    hideError("password");

    if (newElement === repeatElement) {
        changeUserInfo(newElement, pass, "password");
    } else {
        showError("password", "New passwords do not match");
    }
}

function usernameCheck() {
    const newElement = document.getElementById("newUsername").value;
    const repeatElement = document.getElementById("repeatUsername").value;
    const pass = document.getElementById("pass_username").value;

    hideError("username");

    if (newElement === repeatElement) {
        changeUserInfo(newElement, pass, "username");
    } else {
        showError("username", "Usernames do not match");
    }
}

function emailCheck() {
    const newElement = document.getElementById("newEmail").value;
    const repeatElement = document.getElementById("repeatEmail").value;
    const pass = document.getElementById("pass_email").value;

    hideError("email");

    if (newElement === repeatElement) {
        changeUserInfo(newElement, pass, "email");
    } else {
        showError("email", "Emails do not match");
    }
}

