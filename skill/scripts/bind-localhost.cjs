// Node-Preload: zwingt jeden net.Server.listen() ohne Host auf 127.0.0.1.
// marp-cli bindet seinen Vorschau-Server sonst an alle Netzwerkschnittstellen (kein HOST-Parameter).
// Nutzung: NODE_OPTIONS="--require /pfad/bind-localhost.cjs"
const net = require('net');
const orig = net.Server.prototype.listen;
const LOOPBACK = '127.0.0.1';

net.Server.prototype.listen = function (...args) {
  const first = args[0];
  if (typeof first === 'number' || (typeof first === 'string' && /^\d+$/.test(first))) {
    // listen(port[, host][, backlog][, callback])
    if (typeof args[1] !== 'string') args.splice(1, 0, LOOPBACK);
  } else if (first && typeof first === 'object' && first.port !== undefined && !first.host) {
    args[0] = { ...first, host: LOOPBACK };
  }
  return orig.apply(this, args);
};
