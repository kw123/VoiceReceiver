# VoiceReceiver

An [Indigo](https://www.indigodomo.com/) plugin that turns free-form spoken (dictated) phrases into Indigo device, variable, and action commands — and speaks the result back to you.

You talk to an iPhone/iPad/Mac shortcut ("hey Siri, indigo… *turn on the office lights*"); the shortcut drops the text into an Indigo variable; this plugin parses it, executes the matching command, and writes a spoken confirmation back to a second variable that the shortcut reads aloud.

- **Bundle id:** `com.karlwachs.VoiceReceiver`
- **Version:** 2022.4.3
- **Indigo Server API:** 3.0 (Python 3)
- **Author:** Karl Wachs
- **Support:** [Indigo forum (f=164)](http://forums.indigodomo.com/viewforum.php?f=164)

---

## How it works

```
 iPhone / iPad / Mac                Indigo Server
 ┌─────────────────┐               ┌──────────────────────────────┐
 │ Siri Shortcut   │  POST text →  │ command  variable             │
 │  - dictate text │               │      ↓                        │
 │  - send to var  │               │ VoiceReceiver plugin          │
 │  - read feedback│               │   normalize → match → execute │
 │    aloud        │  ← GET text   │      ↓                        │
 └─────────────────┘               │ feedback variable             │
                                   └──────────────────────────────┘
```

1. **The shortcut** listens (or has a hard-wired command), prepends a timestamp, and POSTs the text into an Indigo *command* variable via the Indigo REST API (`/v2/api/command`), locally or through `indigodomo.net`.
2. **The plugin** watches that variable. On change it:
   - normalizes the text (`_ - ? .` → space, `abcDef` → `abc def`, applies bad→good word maps, maps spoken numbers like `one`/`two` → `1`/`2` in several languages),
   - drops the message if it is older than the allowed delta time or contains a blocked word,
   - matches the phrase against the command grammar and runs it against the target device / variable / action.
3. **Feedback** (blank, `ok`/`not executed`, or detailed text — configurable) is written to the *feedback* variable, which the shortcut speaks back.

---

## Features

- Control devices by **name**, by a user-defined **synonym**, or by explicit **`deviceid:12345:`** / **`variableid:…:`** / **`actionid:…:`**.
- **Command grammar** for on/off, toggle, pulse, dip, dimmer brightness, fan speed, thermostat heat/cool, beep, lock/unlock, set/get variables, get device state, and wait.
- **Run Indigo Action Groups** via spoken synonyms (e.g. say *"open garage"*).
- **Concatenate** multiple commands with `and`, `&`, or `then`.
- **Synonyms** for actions, devices, and variables (defined in plugin menus).
- **Bad-to-good word mapping** to fix misheard dictation (e.g. *"the bug"* → *"debug"*, *"hugh"* → *"hue"*).
- **Blocked words** — any command containing one is ignored (e.g. `alarm`, `lock`).
- **Multi-language** number words and command-word remapping (English, German, French, Spanish; others on request).
- **Spoken feedback** with configurable verbosity.
- **Usage statistics** (how often / when commands were received) and help/config dumps to the Indigo log.

---

## Requirements

- Indigo with Server API **3.0** (Python 3 plugin host).
- An Indigo **REST API key** — get one at <https://www.indigodomo.com/account/authorizations>.
- An Apple device with the **Shortcuts** app (iPhone/iPad/Mac).

---

## Installation

1. Double-click `VoiceReceiver.indigoPlugin` to install it in Indigo, and enable it.
2. Open **Plugins ▸ VoiceReceiver ▸ Configure…** and set the variable/folder names and options (see below). The command and feedback variables are created automatically if they don't already exist.
3. Use the plugin's menu items to define synonyms, word mappings, and blocked words.
4. Build the iPhone shortcut (see [The iPhone/Siri shortcut](#the-iphonesiri-shortcut)).

---

## Plugin configuration

Set in **Configure…**:

- **`allow_delta_time`** — Max age (vs. the message timestamp) a command may have before it is rejected.
- **`expect_time_tag`** — Require a timestamp as the first word of each message.
- **`var_name`** — Name of the **command** variable the plugin listens to (auto-created).
- **`var_name_feedback`** — Name of the **feedback** variable the plugin writes results to (auto-created).
- **`folder_name`** — Variable folder for the above (auto-created).
- **`list_devices_max`** — Max number of devices printed for the `list devices` meta-command.
- **`return_feedback`** — What to send back: *blank*, *ok/not executed*, or *detailed*.
- **`plainactionCommand`** *(enable straight action command)* — When on, lets you run an Indigo Action Group by simply speaking its name (the *plain action command*), without defining a synonym. Matching is by exact name first, then ignoring case/spaces/`/`.
- **Language word maps** — Remap command words to another language, e.g. `on → an`, `set → write`.

## Menu items

**Plugins ▸ VoiceReceiver ▸ …**

- **Define Action / Device / Variable Synonymes** — map a short spoken phrase to a long Indigo action/device/variable name.
- **Define mapping of phrases** — bad → good word replacement for misheard dictation.
- **Block phrases** — phrases (`alarm|lock|enable` syntax) that cause a command to be ignored.
- **Reset stats** — clear usage statistics.
- **Print Help** / **Print Config** — dump the full help and current configuration to the Indigo log.


## Command reference

Substitute the placeholders with a name, a synonym, or an explicit id form (`deviceid:<id>:`, `variableid:<id>:`, `actionid:<id>`). Case is ignored; names are normalized before matching. Parentheses below mark optional filler words.

- **`set variable <variable> to <value>`** — Write a value to a variable (must contain `to`).
- **`get variable <variable>`** — Speak the variable's value.
- **`get <device> state <state>`** — Speak a device state value.
- **`turn on/off <device>`** or **`turn <device> on/off`** — Switch a device on or off.
- **`toggle <device>`** — Toggle a device.
- **`pulse <device> <secs>`** — On for `<secs>` (default 1), then off.
- **`dip <device> <secs>`** — Off for `<secs>` (default 1), then on.
- **`(set) speed <device> (to) <xx>`** — Fan speed (0–4 or 100); `one`/`two` map to `1`/`2`.
- **`(set) bright(ness level) <device> (to) <value> (percent/%)`** — Set dimmer brightness 0–100.
- **`(set) heat (temperature) <device> to <degrees>`** — Thermostat heat setpoint.
- **`(set) cool (temperature) <device> to <degrees>`** — Thermostat cool setpoint.
- **`beep <device>`** — Beep a device.
- **`lock <device>` / `unlock <device>`** — Lock / unlock (device must have `IsLockSubType`).
- **`wait <secs>`** — Pause between concatenated commands.
- **`<action synonym>`** — Run the Indigo Action Group mapped to that synonym (see *Define Action Synonymes*).
- **`<indigo action group name>`** — *Plain ("straight") action command:* speak the name of an Indigo Action Group to run it directly, with no synonym defined. This is **opt-in** — enable *"enable straight action command"* in the plugin config. When enabled, the command is matched against action-group names first by exact name, then by a normalized comparison that ignores case, spaces, and `/`; on a match the action group is executed and the configured `action` feedback is returned.

Concatenate commands with `and`, `&`, or `then`.

### Meta commands

- **`list devices`** — Print up to `list_devices_max` devices to the log.
- **`debug on` / `debug off`** — Enable / disable debug logging.
- **`test`** — Print `test` to the log.
- **`help`** — Print the full help to the log.

### Examples

```
turn on office lights              → turns them on; phone speaks "ok" / "turned on"
turn office lights on              → same (word order is flexible)
turn off deviceid:12345:           → controls the device with id 12345
toggle deviceid:12345:             → toggles that device
pulse deviceid:12345: 5 sec        → on for 5 s, then off
dip office lights                  → off 1 s, then on (1 s is the default)
open garage                        → runs the action defined under synonym "open garage"
good night                         → plain action command: runs the Action Group named exactly "good night"
actionid:54321                     → runs Indigo action 54321
bright lamp to 40 and wait 5 and turn on fan   → three commands in sequence
```

---

## The iPhone/Siri shortcut

A ready-made shortcut (with blank keys) is available:
<https://www.icloud.com/shortcuts/4ae22c3cfefc4861a627daa6afff3551>

After importing, replace the placeholders:

- `<your id>` — your indigodomo.net user id
- `<indigo variable id command>` — id of the **command** variable
- `<indigo variable id feedback>` — id of the **feedback** variable
- `192.168.1.` — the first octets of your local network (to detect "at home")
- `<your key>` — your Indigo REST API key

The shortcut dictates text, prepends a timestamp, then POSTs `indigovariable.updateValue` to `…:8176/v2/api/command` (local) or `https://<your id>indigodomo.net/v2/api/command` (remote), and GETs the feedback variable to speak the result. Full step-by-step instructions are in the plugin's **Print Help** output.

> Tip: add a *Vocal Shortcut* (Settings ▸ Accessibility ▸ Vocal Shortcuts) like *"hey indigo do"* so you can trigger it hands-free, then say your command after the pause.

---

## Notes & troubleshooting

- Names are normalized on both sides before matching (`abcDef` → `abc def`; `_ - ? .` → space), so spoken and Indigo names line up more easily.
- Siri sometimes dictates number words; the plugin maps `zero…twelve` → `0…12` (also in German/French/Spanish).
- Use **Print Config** to see the active variable names, feedback mode, word maps, and all defined synonyms; use **Print Help** for the complete command grammar and shortcut build steps.
- If a command fails, the phone speaks *"not executed"* or *"device not found"* (when detailed feedback is enabled).

## Files

- **`Contents/Server Plugin/plugin.py`** — Main plugin logic (command parsing, execution, feedback, menus).
- **`Contents/Server Plugin/checkIndigoPluginName.py`** — Plugin-name sanity check helper.
- **`Contents/Server Plugin/Actions.xml`** — Action definitions (Boost thermostat).
- **`Contents/Server Plugin/MenuItems.xml`** — Menu items (synonyms, word maps, blocked words, help/config/stats).
- **`Contents/Server Plugin/Events.xml`, `Devices.xml`, `PluginConfig.xml`** — Indigo trigger/device/config UI definitions.
- **`Contents/changeLog.txt`** — Version history.

See `Contents/changeLog.txt` for the full change history.
