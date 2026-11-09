"use strict";

const history = [];

function el(id) {
  return document.getElementById(id);
}

function appendMessage(role, text) {
  const windowEl = el("chat-window");
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  windowEl.appendChild(wrapper);
  windowEl.scrollTop = windowEl.scrollHeight;
}

function pushHistory(role, content) {
  history.push({ role, content });
  if (history.length > 40) {
    history.splice(0, history.length - 40);
  }
}

async function loadCapabilities() {
  const response = await fetch("/api/capabilities");
  const data = await response.json();

  const resourceList = el("resource-list");
  data.resources.forEach((resource) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.textContent = resource.name;
    btn.addEventListener("click", async () => {
      const res = await fetch(`/api/resources/${resource.slug}`);
      const body = await res.json();
      el("doc-title").textContent = body.name;
      el("doc-content").textContent = body.content;
      el("doc-dialog").showModal();
    });
    li.appendChild(btn);
    resourceList.appendChild(li);
  });

  const toolList = el("tool-list");
  data.tools.forEach((tool) => {
    const li = document.createElement("li");
    li.textContent = `${tool.name} — ${tool.description}`;
    toolList.appendChild(li);
  });

  const promptList = el("prompt-list");
  data.prompts.forEach((prompt) => {
    const li = document.createElement("li");
    li.textContent = prompt.name;
    li.title = prompt.description;
    promptList.appendChild(li);
  });
}

async function submitChat(event) {
  event.preventDefault();
  const input = el("chat-input");
  const text = input.value.trim();
  if (!text) {
    return;
  }
  input.value = "";
  appendMessage("user", text);
  pushHistory("user", text);

  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: history }),
  });
  const data = await response.json();
  appendMessage("assistant", data.answer || "（无回复）");
  pushHistory("assistant", data.answer || "");
}

async function submitQuery(event) {
  event.preventDefault();
  const orderId = el("query-order-id").value.trim();
  const result = el("query-result");
  if (!orderId) {
    return;
  }
  result.textContent = "查询中…";
  const response = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_id: orderId }),
  });
  const data = await response.json();
  result.textContent = JSON.stringify(data, null, 2);
}

let pendingRefund = null;

function submitRefund(event) {
  event.preventDefault();
  const orderId = el("refund-order-id").value.trim();
  const reason = el("refund-reason").value.trim();
  if (!orderId) {
    return;
  }
  pendingRefund = { order_id: orderId, reason };
  el("confirm-text").textContent = `确认对订单 ${orderId} 执行全额退款？`;
  el("confirm-dialog").showModal();
}

async function confirmRefund() {
  el("confirm-dialog").close();
  const result = el("refund-result");
  result.textContent = "退款处理中…";
  const response = await fetch("/api/refund", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pendingRefund),
  });
  const data = await response.json();
  result.textContent = JSON.stringify(data, null, 2);
  pendingRefund = null;
}

el("chat-form").addEventListener("submit", submitChat);
el("query-form").addEventListener("submit", submitQuery);
el("refund-form").addEventListener("submit", submitRefund);
el("confirm-ok").addEventListener("click", confirmRefund);
el("confirm-cancel").addEventListener("click", () => {
  el("confirm-dialog").close();
  pendingRefund = null;
});
el("doc-close").addEventListener("click", () => el("doc-dialog").close());

loadCapabilities();

