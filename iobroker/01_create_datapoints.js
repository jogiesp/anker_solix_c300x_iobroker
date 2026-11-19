// ioBroker JavaScript-Adapter: EINMAL starten, danach stoppen.
// Run ONCE in the ioBroker JavaScript adapter, then stop it.
// Legt die Soll-Datenpunkte an / creates the target datapoints.

createState('0_userdata.0.Anker.c300x_12V_Ausgang', {
    name: 'C300X 12V Ausgang (Soll)',
    type: 'boolean',
    role: 'switch',
    read: true,
    write: true,
    def: false
});

createState('0_userdata.0.Anker.c300x_AC_Ausgang', {
    name: 'C300X AC Ausgang (Soll)',
    type: 'boolean',
    role: 'switch',
    read: true,
    write: true,
    def: false
});

createState('0_userdata.0.Anker.c300x_Licht', {
    name: 'C300X Licht (Soll)',
    type: 'number',
    role: 'level',
    read: true,
    write: true,
    min: 0,
    max: 4,
    states: { 0: 'Aus', 1: 'Niedrig', 2: 'Mittel', 3: 'Hoch', 4: 'Blinken' },
    def: 0
});

log('Datenpunkte 12V, AC und Licht wurden angelegt.', 'info');
