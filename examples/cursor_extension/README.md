# MemMachine

This is the extension for MemMachine, which lets you leverage its capabilities within the Cursor editor.

## Features

MemMachine provides powerful memory management capabilities directly within your Cursor editor environment.

### Memory Panels

The extension includes two dedicated panels for viewing different types of memories retrieved from the MemMachine API:

#### Episodic Memory Panel
- A list of episodic memories with titles, content previews, and metadata
- Built-in refresh button at the top of the panel
- Interactive memory selection with click-to-view details
- Loading indicators during data refresh
- Error handling for API connectivity issues

#### Profile Memory Panel
- A list of profile memories with titles, content previews, and metadata
- Built-in refresh button at the top of the panel
- Interactive memory selection with click-to-view details
- Loading indicators during data refresh
- Error handling for API connectivity issues

### Available Commands

- **MemMachine: Hello World** - Basic MemMachine functionality demonstration
- **MemMachine: Hello World 2** - Additional MemMachine features
- **MemMachine: Show Episodic Memory** - Opens the episodic memory panel
- **MemMachine: Show Profile Memory** - Opens the profile memory panel
- **MemMachine: Refresh All Memories** - Refreshes both episodic and profile memory panels

## Requirements

- Cursor editor
- VS Code engine version 1.93.0 or higher

## Installation

1. Install the extension from the Cursor marketplace or load it locally
2. The extension will be automatically activated when you use the available commands

## Usage

### Accessing the Memory Panels

1. **Via Command Palette:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
   - Type "MemMachine: Show Episodic Memory" or "MemMachine: Show Profile Memory"
   - Select the command to focus the desired panel

2. **Via Bottom Panel:**
   - Look for the "MemMachine" tab in the bottom panel area
   - Click on "Episodic Memory" to view your episodic memories
   - Click on "Profile Memory" to view your profile memories

Both memory panels appear in the bottom panel area as part of the MemMachine view container, alongside other panels like Output, Problems, Terminal, etc.

### API Configuration

The extension connects to the MemMachine API at `http://18.116.238.202:8001`. The memory panels will automatically fetch data from their respective endpoints:
- Episodic Memory panel: `/memory/get_episodic_memory`
- Profile Memory panel: `/memory/get_profile_memory`

### Other Commands

You can access other MemMachine features through the Command Palette:

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. Type "MemMachine" to see available commands
3. Select the desired MemMachine command

## Release Notes

### 0.0.1

Initial release of MemMachine extension for Cursor editor.

## Contributing

This extension is developed by MemVerge. For issues or feature requests, please contact the development team.

## License

This extension is proprietary software developed by MemVerge.
