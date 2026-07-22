(function () {
  var root = document.getElementById("chat-root");
  if (!root) return;

  var room = root.dataset.room;
  var currentUserId = parseInt(root.dataset.currentUserId, 10);
  var messagesEl = document.getElementById("chat-messages");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  scrollToBottom();

  var socket = io();

  socket.on("connect", function () {
    socket.emit("join", { room: room });
  });

  socket.on("new_message", function (data) {
    if (data.room !== room) return;

    var wrapper = document.createElement("div");
    wrapper.className = "chat-msg" + (data.sender_id === currentUserId ? " mine" : "");

    var meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent =
      data.sender +
      " · " +
      new Date(data.created_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });

    // textContent (never innerHTML) so any HTML a user types renders as
    // plain text instead of being parsed — this is what actually prevents
    // DOM XSS via chat content on the client, on top of server-side
    // sanitization in app/sockets.py.
    var text = document.createElement("div");
    text.className = "text";
    text.textContent = data.content;

    wrapper.appendChild(meta);
    wrapper.appendChild(text);
    messagesEl.appendChild(wrapper);
    scrollToBottom();
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var content = input.value.trim();
    if (!content) return;
    socket.emit("send_message", { room: room, content: content });
    input.value = "";
  });
})();
