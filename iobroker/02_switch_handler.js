// ioBroker JavaScript-Adapter: dauerhaft laufen lassen.
// Keep this running in the ioBroker JavaScript adapter.
// Reagiert auf Aenderungen der Datenpunkte und startet solix_switch.py.
// Reacts to datapoint changes and runs solix_switch.py.
//
// ANPASSEN / CHANGE: PY und SCRIPT auf deine Pfade, USER muss der Benutzer sein,
// dem die .env gehoert (siehe sudoers/install_sudoers.sh).

const ID_DC = '0_userdata.0.Anker.c300x_12V_Ausgang';
const ID_AC = '0_userdata.0.Anker.c300x_AC_Ausgang';
const ID_LIGHT = '0_userdata.0.Anker.c300x_Licht';
const USER = 'pi';
const PY = '/home/pi/anker-solix-api/.venv/bin/python';
const SCRIPT = '/home/pi/anker-solix-api/solix_switch.py';
const LIGHT = ['off', 'low', 'medium', 'high', 'blinking'];

function run(label, args, id, val) {
    log(label + ': ' + args, 'info');
    exec(`sudo -n -u ${USER} ${PY} ${SCRIPT} ${args}`, (err, stdout, stderr) => {
        if (err) {
            log(label + ' Fehler: ' + (stderr || err), 'error');
        } else {
            log(label + ': ' + stdout.trim().split('\n').pop(), 'info');
            setState(id, val, true);
        }
    });
}

on({ id: ID_DC, change: 'ne', ack: false }, (obj) => {
    run('12V-Ausgang', 'dc ' + (obj.state.val ? 'on' : 'off'), ID_DC, obj.state.val);
});

on({ id: ID_AC, change: 'ne', ack: false }, (obj) => {
    run('AC-Ausgang', 'ac ' + (obj.state.val ? 'on' : 'off'), ID_AC, obj.state.val);
});

on({ id: ID_LIGHT, change: 'ne', ack: false }, (obj) => {
    const mode = LIGHT[Number(obj.state.val)];
    if (!mode) {
        log('Licht: ungueltiger Wert ' + obj.state.val, 'error');
        return;
    }
    run('Licht', 'light ' + mode, ID_LIGHT, obj.state.val);
});

log('Wartet auf Aenderungen von 12V, AC und Licht', 'info');
