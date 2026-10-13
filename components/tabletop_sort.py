"""Interactive tabletop component for direct-manipulation card sorting."""

from typing import Callable, Dict, Any

import streamlit as st


TABLETOP_HTML = """
<div class="tabletop-root">
  <div class="tabletop-toolbar">
    <div>
      <div class="tabletop-title">Interactive sorting workspace</div>
      <div id="tabletop-progress" class="tabletop-progress"></div>
    </div>
    <button id="tabletop-undo" class="undo-button" type="button">Undo last move</button>
  </div>

  <div id="tabletop-status" class="sr-only" role="status" aria-live="polite"></div>

  <div id="tabletop-detail" class="selection-panel" hidden>
    <div class="selection-eyebrow">Selected item</div>
    <div id="tabletop-detail-title" class="selection-title"></div>
    <div id="tabletop-detail-description" class="selection-description"></div>
    <div id="tabletop-detail-example" class="selection-example"></div>
    <div class="selection-help">Now click a category bin, drag the item there, or press Escape to cancel.</div>
  </div>

  <div class="tabletop-workspace">
    <section id="tabletop-unsorted" class="card-bin unsorted-bin">
      <div class="bin-heading-row">
        <div>
          <div class="bin-kicker">Item tray</div>
          <div class="bin-title">Unsorted <span id="tabletop-unsorted-count" class="bin-count"></span></div>
        </div>
        <button id="tabletop-unassign" class="place-button" type="button">Move selected here</button>
      </div>
      <label class="search-label" for="tabletop-search">Find an unsorted item</label>
      <input id="tabletop-search" class="card-search" type="search" placeholder="Search items…" />
      <div id="tabletop-unsorted-cards" class="card-list tray-list"></div>
    </section>

    <div id="tabletop-bins" class="category-area"></div>
  </div>
</div>
"""


TABLETOP_CSS = """
:host {
  display: block;
  width: 100%;
  color: var(--st-text-color, #0f172a);
  font-family: var(--st-font, sans-serif);
}

* { box-sizing: border-box; }

.tabletop-root {
  width: 100%;
  border: 1px solid var(--st-border-color, #cbd5e1);
  border-radius: 14px;
  background: var(--st-background-color, #ffffff);
  padding: 1rem;
}

.tabletop-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: .8rem;
}

.tabletop-title { font-size: 1.05rem; font-weight: 750; }
.tabletop-progress { color: var(--st-text-color, #475569); font-size: .9rem; margin-top: .15rem; opacity: .8; }

.undo-button, .place-button {
  appearance: none;
  border: 1px solid var(--st-primary-color, #2563eb);
  border-radius: 8px;
  background: transparent;
  color: var(--st-primary-color, #2563eb);
  cursor: pointer;
  font: inherit;
  font-weight: 650;
  padding: .45rem .7rem;
}

.undo-button:hover, .place-button:hover { background: color-mix(in srgb, var(--st-primary-color, #2563eb) 10%, transparent); }
.undo-button:disabled, .place-button:disabled { cursor: not-allowed; opacity: .45; }

.selection-panel {
  position: sticky;
  top: .5rem;
  z-index: 4;
  border: 2px solid var(--st-primary-color, #2563eb);
  border-radius: 12px;
  background: var(--st-secondary-background-color, #f8fafc);
  box-shadow: 0 5px 14px rgba(15, 23, 42, .12);
  margin-bottom: .9rem;
  padding: .85rem 1rem;
}

.selection-eyebrow, .bin-kicker {
  color: var(--st-primary-color, #2563eb);
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .06em;
  text-transform: uppercase;
}

.selection-title { font-size: 1.05rem; font-weight: 750; line-height: 1.35; margin-top: .18rem; }
.selection-description { line-height: 1.45; margin-top: .45rem; }
.selection-example { font-size: .9rem; font-style: italic; margin-top: .4rem; opacity: .82; }
.selection-help { font-size: .82rem; font-weight: 650; margin-top: .55rem; color: var(--st-primary-color, #2563eb); }

.tabletop-workspace {
  display: grid;
  grid-template-columns: minmax(245px, .72fr) minmax(0, 2fr);
  gap: .9rem;
  align-items: start;
}

.card-bin {
  border: 2px dashed var(--st-border-color, #94a3b8);
  border-radius: 12px;
  background: var(--st-secondary-background-color, #f8fafc);
  min-height: 150px;
  padding: .75rem;
  transition: border-color .14s ease, box-shadow .14s ease, transform .14s ease;
}

.card-bin.is-target { border-color: var(--st-primary-color, #2563eb); box-shadow: 0 0 0 3px color-mix(in srgb, var(--st-primary-color, #2563eb) 18%, transparent); cursor: pointer; }
.card-bin.drag-over { border-style: solid; border-color: var(--st-primary-color, #2563eb); transform: translateY(-2px); }

.unsorted-bin { position: static; }

.bin-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: .55rem;
  border-radius: 8px;
  margin-bottom: .55rem;
  padding: .15rem;
}

.bin-title { font-size: .98rem; font-weight: 800; line-height: 1.25; }
.bin-count { font-size: .8rem; font-weight: 650; opacity: .75; }
.bin-description { font-size: .78rem; line-height: 1.35; margin: -.2rem 0 .55rem; opacity: .75; }

.search-label { display: block; font-size: .75rem; font-weight: 650; margin: .35rem 0 .2rem; }
.card-search {
  width: 100%;
  border: 1px solid var(--st-border-color, #cbd5e1);
  border-radius: 8px;
  background: var(--st-background-color, #fff);
  color: var(--st-text-color, #0f172a);
  font: inherit;
  padding: .48rem .6rem;
  margin-bottom: .45rem;
}

.category-area {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: .75rem;
  max-height: 780px;
  overflow: auto;
  padding: 3px;
}

.freeform-mode .tabletop-workspace { grid-template-columns: minmax(230px, .58fr) minmax(0, 2.4fr); }
.freeform-mode .category-area {
  align-content: start;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--st-border-color, #cbd5e1) 28%, transparent) 1px, transparent 1px),
    linear-gradient(color-mix(in srgb, var(--st-border-color, #cbd5e1) 28%, transparent) 1px, transparent 1px),
    var(--st-secondary-background-color, #f8fafc);
  background-size: 22px 22px;
  border: 1px solid var(--st-border-color, #cbd5e1);
  border-radius: 12px;
  max-height: none;
  min-height: 520px;
  overflow: visible;
  padding: .85rem;
}
.freeform-mode .card-bin { background: var(--st-background-color, #fff); box-shadow: 0 2px 7px rgba(15, 23, 42, .08); }
.freeform-mode .bin-card-list { max-height: 390px; }
.new-pile-zone {
  align-items: center;
  border: 2px dashed var(--st-primary-color, #2563eb);
  color: var(--st-primary-color, #2563eb);
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 170px;
  text-align: center;
}
.new-pile-zone.is-target { background: color-mix(in srgb, var(--st-primary-color, #2563eb) 8%, transparent); }
.new-pile-title { font-size: .95rem; font-weight: 800; }
.new-pile-copy { font-size: .82rem; line-height: 1.4; margin-top: .35rem; max-width: 250px; opacity: .86; }
.pile-composer { width: 100%; }
.pile-composer label { display: block; font-size: .78rem; font-weight: 750; margin-bottom: .35rem; }
.pile-composer-row { display: flex; gap: .4rem; }
.pile-composer input { min-width: 0; flex: 1; }
.pile-composer-cancel { background: transparent; border: 0; color: inherit; cursor: pointer; font: inherit; margin-top: .45rem; text-decoration: underline; }

.card-list { display: flex; flex-direction: column; gap: .42rem; }
.tray-list { max-height: 650px; overflow: auto; padding: 2px; }
.bin-card-list { max-height: 330px; overflow: auto; padding: 2px; }

.sort-card {
  appearance: none;
  width: 100%;
  border: 1px solid var(--card-border, #94a3b8);
  border-left: 5px solid var(--card-border, #2563eb);
  border-radius: 9px;
  background: var(--card-fill, #eff6ff);
  color: var(--card-text, #0f172a);
  cursor: grab;
  font: inherit;
  padding: .62rem .68rem;
  text-align: left;
  touch-action: manipulation;
  transition: box-shadow .12s ease, transform .12s ease;
}

.sort-card:hover { box-shadow: 0 3px 8px rgba(15, 23, 42, .12); transform: translateY(-1px); }
.sort-card:active { cursor: grabbing; }
.sort-card.is-selected { outline: 3px solid var(--st-primary-color, #2563eb); outline-offset: 1px; }
.sort-card.is-dragging { opacity: .55; }
.sort-card-title {
  display: -webkit-box;
  overflow: hidden;
  font-size: .88rem;
  font-weight: 700;
  line-height: 1.3;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.empty-message { font-size: .82rem; font-style: italic; opacity: .65; padding: .55rem .1rem; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }

button:focus-visible, input:focus-visible { outline: 3px solid var(--st-primary-color, #2563eb); outline-offset: 2px; }

@media (max-width: 760px) {
  .tabletop-root { padding: .7rem; }
  .tabletop-toolbar { align-items: flex-start; }
  .tabletop-workspace { grid-template-columns: 1fr; }
  .unsorted-bin { position: static; }
  .tray-list { max-height: 350px; }
  .category-area { grid-template-columns: 1fr; max-height: none; overflow: visible; }
  .freeform-mode .tabletop-workspace { grid-template-columns: 1fr; }
  .freeform-mode .category-area { min-height: 0; }
  .bin-card-list { max-height: 280px; }
}
"""


TABLETOP_JS = r"""
export default function(component) {
  const { parentElement, data, setStateValue } = component;
  const cards = Array.isArray(data?.cards) ? data.cards : [];
  const categories = Array.isArray(data?.categories) ? data.categories : [];
  const itemLabel = String(data?.item_label || "item").trim().toLowerCase() || "item";
  const pluralLabel = String(data?.plural_label || `${itemLabel}s`).trim().toLowerCase() || `${itemLabel}s`;
  const isFreeform = data?.mode === "FREEFORM";
  const canCreate = Boolean(data?.can_create);
  let placements = JSON.parse(JSON.stringify(data?.placements || {}));
  let selectedCardId = null;
  let pendingPileCardId = null;
  let searchTerm = "";

  const progress = parentElement.querySelector("#tabletop-progress");
  const status = parentElement.querySelector("#tabletop-status");
  const detail = parentElement.querySelector("#tabletop-detail");
  const detailTitle = parentElement.querySelector("#tabletop-detail-title");
  const detailDescription = parentElement.querySelector("#tabletop-detail-description");
  const detailExample = parentElement.querySelector("#tabletop-detail-example");
  const undoButton = parentElement.querySelector("#tabletop-undo");
  const unsortedBin = parentElement.querySelector("#tabletop-unsorted");
  const unsortedCount = parentElement.querySelector("#tabletop-unsorted-count");
  const unsortedCards = parentElement.querySelector("#tabletop-unsorted-cards");
  const unassignButton = parentElement.querySelector("#tabletop-unassign");
  const search = parentElement.querySelector("#tabletop-search");
  const bins = parentElement.querySelector("#tabletop-bins");

  parentElement.querySelector(".tabletop-root")?.classList.toggle("freeform-mode", isFreeform);

  const makeEventId = () => {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  const cardById = id => cards.find(card => card.id === id);
  const knownTargets = () => ["Unassigned", ...categories.map(category => category.name)];

  function sourceFor(cardId) {
    for (const [category, ids] of Object.entries(placements)) {
      if (Array.isArray(ids) && ids.includes(cardId)) return category;
    }
    return null;
  }

  function moveLocally(cardId, target) {
    for (const category of Object.keys(placements)) {
      placements[category] = (placements[category] || []).filter(id => id !== cardId);
    }
    if (!Array.isArray(placements[target])) placements[target] = [];
    placements[target].push(cardId);
  }

  function announce(message) {
    status.textContent = "";
    requestAnimationFrame(() => { status.textContent = message; });
  }

  function focusCard(cardId) {
    return Array.from(parentElement.querySelectorAll(".sort-card"))
      .find(element => element.dataset.cardId === cardId)?.focus();
  }

  function focusAfterMove(cardId, source) {
    requestAnimationFrame(() => {
      if (source !== "Unassigned") {
        focusCard(cardId);
        return;
      }
      const nextUnsorted = Array.isArray(placements.Unassigned) ? placements.Unassigned[0] : null;
      if (nextUnsorted) focusCard(nextUnsorted);
      else undoButton.focus();
    });
  }

  function commitMove(cardId, target, method) {
    if (!cardById(cardId) || !knownTargets().includes(target)) return;
    const source = sourceFor(cardId);
    if (!source || source === target) {
      selectedCardId = null;
      render();
      return;
    }
    moveLocally(cardId, target);
    selectedCardId = null;
    render();
    if (method === "keyboard") focusAfterMove(cardId, source);
    setStateValue("move", {
      event_id: makeEventId(),
      card_id: cardId,
      source_category: source,
      target_category: target,
      method: method,
    });
  }

  function beginNewPile(cardId, moveKeyboardFocus = false) {
    if (!isFreeform || !canCreate || !cardById(cardId)) return;
    pendingPileCardId = cardId;
    selectedCardId = null;
    render();
    announce(`Name the new pile for ${cardById(cardId)?.title || "this item"}.`);
    if (moveKeyboardFocus) {
      requestAnimationFrame(() => parentElement.querySelector(".pile-composer input")?.focus());
    }
  }

  function selectCard(cardId, moveKeyboardFocus) {
    pendingPileCardId = null;
    selectedCardId = selectedCardId === cardId ? null : cardId;
    render();
    if (selectedCardId) announce(`${cardById(cardId)?.title || "Item"} selected. Choose a category.`);
    else announce("Item selection cleared.");
    if (moveKeyboardFocus) {
      requestAnimationFrame(() => {
        if (selectedCardId) {
          const destination = parentElement.querySelector(".category-area .place-button:not(:disabled)");
          if (destination) destination.focus();
          else if (isFreeform && canCreate) parentElement.querySelector(".new-pile-zone")?.focus();
          else if (!unassignButton.disabled) unassignButton.focus();
          else focusCard(cardId);
          return;
        }
        focusCard(cardId);
      });
    }
  }

  function makeCard(card) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `sort-card${selectedCardId === card.id ? " is-selected" : ""}`;
    button.draggable = true;
    button.dataset.cardId = card.id;
    button.setAttribute("aria-pressed", selectedCardId === card.id ? "true" : "false");
    button.setAttribute("aria-label", `${card.title}. Select this ${itemLabel} to move it.`);
    button.style.setProperty("--card-fill", card.fill || "#EFF6FF");
    button.style.setProperty("--card-text", card.text || "#0F172A");
    button.style.setProperty("--card-border", card.border || "#2563EB");

    const title = document.createElement("span");
    title.className = "sort-card-title";
    title.textContent = card.title;
    button.appendChild(title);

    button.onclick = event => {
      event.stopPropagation();
      selectCard(card.id, false);
    };
    button.onkeydown = event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      event.stopPropagation();
      selectCard(card.id, true);
    };
    button.ondragstart = event => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.id);
      button.classList.add("is-dragging");
    };
    button.ondragend = () => {
      button.classList.remove("is-dragging");
      parentElement.querySelectorAll(".drag-over").forEach(element => element.classList.remove("drag-over"));
    };
    return button;
  }

  function wireDropZone(element, target) {
    element.ondragenter = event => {
      event.preventDefault();
      element.classList.add("drag-over");
    };
    element.ondragover = event => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    };
    element.ondragleave = event => {
      if (!element.contains(event.relatedTarget)) element.classList.remove("drag-over");
    };
    element.ondrop = event => {
      event.preventDefault();
      element.classList.remove("drag-over");
      commitMove(event.dataTransfer.getData("text/plain"), target, "drag");
    };
  }

  function placeSelected(target, method) {
    if (selectedCardId) commitMove(selectedCardId, target, method);
  }

  function renderDetail() {
    const card = selectedCardId ? cardById(selectedCardId) : null;
    detail.hidden = !card;
    if (!card) return;
    detailTitle.textContent = card.title;
    detailDescription.textContent = card.description || "";
    detailDescription.hidden = !card.description;
    detailExample.textContent = card.example ? `Example: ${card.example}` : "";
    detailExample.hidden = !card.example;
  }

  function addCards(container, ids, emptyText) {
    container.replaceChildren();
    if (!ids.length) {
      const empty = document.createElement("div");
      empty.className = "empty-message";
      empty.textContent = emptyText;
      container.appendChild(empty);
      return;
    }
    ids.forEach(id => {
      const card = cardById(id);
      if (card) container.appendChild(makeCard(card));
    });
  }

  function renderCategory(category) {
    const section = document.createElement("section");
    const sourceCategory = selectedCardId ? sourceFor(selectedCardId) : null;
    section.className = `card-bin${selectedCardId && sourceCategory !== category.name ? " is-target" : ""}`;
    section.setAttribute("aria-label", `${category.name} category bin`);
    section.style.borderColor = category.border || "#0284C7";
    wireDropZone(section, category.name);

    const heading = document.createElement("div");
    heading.className = "bin-heading-row";
    heading.style.background = category.fill || "#E0F2FE";
    heading.style.color = category.text || "#0C4A6E";

    const label = document.createElement("div");
    const kicker = document.createElement("div");
    kicker.className = "bin-kicker";
    kicker.textContent = "Category bin";
    const title = document.createElement("div");
    title.className = "bin-title";
    const ids = Array.isArray(placements[category.name]) ? placements[category.name] : [];
    title.textContent = `${category.name} (${ids.length})`;
    label.append(kicker, title);

    const place = document.createElement("button");
    place.type = "button";
    place.className = "place-button";
    place.textContent = "Place here";
    place.disabled = !selectedCardId || sourceCategory === category.name;
    place.setAttribute("aria-label", `Place selected ${itemLabel} in ${category.name}`);
    place.onclick = event => {
      event.stopPropagation();
      placeSelected(category.name, "click");
    };
    place.onkeydown = event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      event.stopPropagation();
      placeSelected(category.name, "keyboard");
    };
    heading.append(label, place);
    section.appendChild(heading);

    if (category.description) {
      const description = document.createElement("div");
      description.className = "bin-description";
      description.textContent = category.description;
      section.appendChild(description);
    }

    const list = document.createElement("div");
    list.className = "card-list bin-card-list";
    addCards(list, ids, `No ${pluralLabel} here yet. Drag one here or select an item and click Place here.`);
    section.appendChild(list);
    section.onclick = event => {
      if (!selectedCardId) return;
      if (event.target.closest(".sort-card") || event.target.closest(".place-button")) return;
      if (sourceFor(selectedCardId) === category.name) return;
      placeSelected(category.name, "click");
    };
    return section;
  }

  function renderNewPileZone() {
    const section = document.createElement("section");
    section.className = `card-bin new-pile-zone${selectedCardId ? " is-target" : ""}`;
    section.tabIndex = 0;
    section.setAttribute("role", "button");
    section.setAttribute(
      "aria-label",
      pendingPileCardId
        ? `Name a new pile for ${cardById(pendingPileCardId)?.title || "the selected item"}`
        : `Create a new category pile${selectedCardId ? " with the selected item" : ""}`,
    );

    const beginFromDrop = event => {
      event.preventDefault();
      section.classList.remove("drag-over");
      beginNewPile(event.dataTransfer.getData("text/plain"));
    };
    section.ondragenter = event => {
      event.preventDefault();
      section.classList.add("drag-over");
    };
    section.ondragover = event => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    };
    section.ondragleave = event => {
      if (!section.contains(event.relatedTarget)) section.classList.remove("drag-over");
    };
    section.ondrop = beginFromDrop;

    if (!pendingPileCardId) {
      const title = document.createElement("div");
      title.className = "new-pile-title";
      title.textContent = selectedCardId ? "Create a new pile here" : "Create a new pile";
      const copy = document.createElement("div");
      copy.className = "new-pile-copy";
      copy.textContent = selectedCardId
        ? `Click here to name a new pile for the selected ${itemLabel}, or drag an item here.`
        : `Drag an item here to start a new category pile.`;
      section.append(title, copy);
      section.onclick = event => {
        if (event.target.closest("input, button")) return;
        if (selectedCardId) beginNewPile(selectedCardId, false);
      };
      section.onkeydown = event => {
        if ((event.key === "Enter" || event.key === " ") && selectedCardId) {
          event.preventDefault();
          beginNewPile(selectedCardId, true);
        }
      };
      return section;
    }

    const pendingCard = cardById(pendingPileCardId);
    const composer = document.createElement("div");
    composer.className = "pile-composer";
    const label = document.createElement("label");
    label.textContent = `Name the new pile for ${pendingCard?.title || "this item"}`;
    label.htmlFor = "new-pile-name";
    const row = document.createElement("div");
    row.className = "pile-composer-row";
    const input = document.createElement("input");
    input.id = "new-pile-name";
    input.type = "text";
    input.placeholder = "e.g., Related ideas";
    input.autocomplete = "off";
    input.maxLength = 120;
    const create = document.createElement("button");
    create.type = "button";
    create.className = "place-button";
    create.textContent = "Create pile";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "pile-composer-cancel";
    cancel.textContent = "Cancel";
    const submit = method => {
      const name = input.value.trim();
      if (!name) {
        announce("Enter a name for the new pile.");
        input.focus();
        return;
      }
      setStateValue("create", {
        event_id: makeEventId(),
        card_id: pendingPileCardId,
        category_name: name,
        method,
      });
    };
    create.onclick = event => {
      event.stopPropagation();
      submit("click");
    };
    create.onkeydown = event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      event.stopPropagation();
      submit("keyboard");
    };
    input.onkeydown = event => {
      if (event.key === "Enter") {
        event.preventDefault();
        submit("keyboard");
      }
      if (event.key === "Escape") {
        event.preventDefault();
        pendingPileCardId = null;
        render();
      }
    };
    cancel.onclick = event => {
      event.stopPropagation();
      pendingPileCardId = null;
      render();
    };
    row.append(input, create);
    composer.append(label, row, cancel);
    section.appendChild(composer);
    return section;
  }

  function render() {
    const unsortedIds = Array.isArray(placements.Unassigned) ? placements.Unassigned : [];
    const placedCount = Math.max(0, cards.length - unsortedIds.length);
    progress.textContent = `${placedCount} of ${cards.length} ${pluralLabel} placed · ${unsortedIds.length} remaining`;
    unsortedCount.textContent = `(${unsortedIds.length})`;
    undoButton.disabled = !data?.can_undo;
    unassignButton.disabled = !selectedCardId || sourceFor(selectedCardId) === "Unassigned";
    unsortedBin.classList.toggle("is-target", Boolean(selectedCardId));

    const filteredIds = unsortedIds.filter(id => {
      const card = cardById(id);
      const searchable = `${card?.title || ""} ${card?.description || ""}`.toLowerCase();
      return searchable.includes(searchTerm);
    });
    addCards(unsortedCards, filteredIds, searchTerm ? `No matching unsorted ${pluralLabel}.` : `All ${pluralLabel} have been placed.`);

    const workspaceNodes = categories.map(renderCategory);
    if (isFreeform && canCreate) workspaceNodes.push(renderNewPileZone());
    bins.replaceChildren(...workspaceNodes);
    renderDetail();
  }

  search.value = "";
  search.oninput = event => {
    searchTerm = event.target.value.toLowerCase().trim();
    render();
    search.focus();
  };
  search.onclick = event => event.stopPropagation();
  unassignButton.onclick = event => {
    event.stopPropagation();
    placeSelected("Unassigned", "click");
  };
  unassignButton.onkeydown = event => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    event.stopPropagation();
    placeSelected("Unassigned", "keyboard");
  };
  undoButton.onclick = () => {
    setStateValue("undo", { event_id: makeEventId(), method: "click" });
  };
  undoButton.onkeydown = event => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    setStateValue("undo", { event_id: makeEventId(), method: "keyboard" });
  };
  wireDropZone(unsortedBin, "Unassigned");

  const handleKeydown = event => {
    if (event.key === "Escape" && selectedCardId) {
      const cancelledCardId = selectedCardId;
      selectedCardId = null;
      render();
      announce("Item selection cleared.");
      requestAnimationFrame(() => focusCard(cancelledCardId));
    }
  };
  parentElement.addEventListener("keydown", handleKeydown);
  render();
  if (data?.announcement) announce(data.announcement);
  if (data?.focus_target) {
    requestAnimationFrame(() => {
      if (data.focus_target.kind === "card") focusCard(data.focus_target.card_id);
      else if (data.focus_target.kind === "undo") undoButton.focus();
    });
  }

  return () => parentElement.removeEventListener("keydown", handleKeydown);
}
"""


def _register_tabletop_component():
    components = getattr(st, "components", None)
    version_two = getattr(components, "v2", None) if components else None
    if version_two is None:
        return None
    return version_two.component(
        "cardsort_interactive_tabletop",
        html=TABLETOP_HTML,
        css=TABLETOP_CSS,
        js=TABLETOP_JS,
    )


_TABLETOP_COMPONENT = _register_tabletop_component()


def render_tabletop_component(
    data: Dict[str, Any],
    *,
    key: str,
    on_move: Callable[[], None],
    on_undo: Callable[[], None],
    on_create: Callable[[], None],
) -> bool:
    """Mount the interactive board and return whether Components v2 is available."""
    if _TABLETOP_COMPONENT is None:
        return False
    _TABLETOP_COMPONENT(
        data=data,
        default={"move": None, "undo": None, "create": None},
        key=key,
        on_move_change=on_move,
        on_undo_change=on_undo,
        on_create_change=on_create,
        width="stretch",
        height="content",
    )
    return True
