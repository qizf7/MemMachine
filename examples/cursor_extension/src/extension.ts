// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { EpisodicMemoryTreeProvider } from './episodicMemoryTreeProvider';
import { ProfileMemoryTreeProvider } from './profileMemoryTreeProvider';
import { MCPServerManager } from './mcpServerManager';
import { MCP_NAME, MCP_URL, AUTH_TOKEN } from './config';

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

	// Use the console to output diagnostic information (console.log) and errors (console.error)
	// This line of code will only be executed once when your extension is activated
	console.log('Congratulations, your extension "memmachine" is now active!');

	// Initialize MCP Server Manager
	const mcpManager = MCPServerManager.getInstance();
	console.log(`Running in ${mcpManager.getEnvironment()}`);

	// Register the episodic memory tree provider
	const episodicMemoryProvider = new EpisodicMemoryTreeProvider();
	context.subscriptions.push(
		vscode.window.createTreeView('episodicMemoryPanel', {
			treeDataProvider: episodicMemoryProvider
		})
	);

	// // Register the profile memory tree provider
	const profileMemoryProvider = new ProfileMemoryTreeProvider();
	context.subscriptions.push(
		vscode.window.createTreeView('profileMemoryPanel', {
			treeDataProvider: profileMemoryProvider
		})
	);

	// The command has been defined in the package.json file
	// Now provide the implementation of the command with registerCommand
	// The commandId parameter must match the command field in package.json
	let disposable = vscode.commands.registerCommand('memmachine.helloWorld', () => {
		// The code you place here will be executed every time your command is executed
		// Display a message box to the user
		vscode.window.showInformationMessage('Hello World from MemMachine! (test)');
	});

	// Register command to show episodic memory panel
	let showEpisodicMemoryDisposable = vscode.commands.registerCommand('memmachine.showEpisodicMemory', () => {
		// Focus on the episodic memory view
		vscode.commands.executeCommand('episodicMemoryPanel.focus');
	});

	// Register command to refresh both memory panels
	let refreshAllMemoriesDisposable = vscode.commands.registerCommand('memmachine.refreshAllMemories', () => {
		episodicMemoryProvider.refresh();
		profileMemoryProvider.refresh();
	});


	// Register command to show profile memory panel
	let showProfileMemoryDisposable = vscode.commands.registerCommand('memmachine.showProfileMemory', () => {
		// Focus on the profile memory view
		vscode.commands.executeCommand('profileMemoryPanel.focus');
	});

	// Keep individual refresh commands for the refresh buttons in panels
	let refreshEpisodicMemoryDisposable = vscode.commands.registerCommand('memmachine.refreshEpisodicMemory', () => {
		episodicMemoryProvider.refresh();
	});

	let refreshProfileMemoryDisposable = vscode.commands.registerCommand('memmachine.refreshProfileMemory', () => {
		profileMemoryProvider.refresh();
	});

	// Register MCP server commands
	let registerMCPServerDisposable = vscode.commands.registerCommand('memmachine.registerMCPServer', async () => {
		const serverName = await vscode.window.showInputBox({
			prompt: 'Enter MCP server name',
		placeHolder: MCP_NAME,
		value: MCP_NAME
		});

		if (!serverName) {
			return;
		}

		const success = await mcpManager.registerServer({
			name: serverName,
			url: MCP_URL,
			headers: {
				'Authorization': `Bearer ${AUTH_TOKEN}`
			}
		});

		if (success) {
			vscode.window.showInformationMessage(`MCP server '${serverName}' registered successfully!`);
		}
	});

	let unregisterMCPServerDisposable = vscode.commands.registerCommand('memmachine.unregisterMCPServer', async () => {
		const registeredServers = mcpManager.getRegisteredServers();
		
		if (registeredServers.length === 0) {
			vscode.window.showInformationMessage('No MCP servers are currently registered.');
			return;
		}

		const serverNames = registeredServers.map(server => server.name);
		const selectedServer = await vscode.window.showQuickPick(serverNames, {
			placeHolder: 'Select MCP server to unregister'
		});

		if (!selectedServer) {
			return;
		}

		const success = await mcpManager.unregisterServer(selectedServer);
		if (success) {
			vscode.window.showInformationMessage(`MCP server '${selectedServer}' unregistered successfully!`);
		}
	});

	// Auto-register default MemMachine server on activation
	let autoRegisterDisposable = vscode.commands.registerCommand('memmachine.autoRegisterDefaultServer', async () => {
		const success = await mcpManager.registerMemMachineServer();
		if (success) {
			console.log('Default MemMachine MCP server registered automatically');
		}
	});


	context.subscriptions.push(
		disposable, 
		showEpisodicMemoryDisposable, 
		refreshAllMemoriesDisposable,
		refreshEpisodicMemoryDisposable, 
		showProfileMemoryDisposable,
		refreshProfileMemoryDisposable,
		registerMCPServerDisposable,
		unregisterMCPServerDisposable,
		autoRegisterDisposable
	);

	// Auto-register the default MemMachine server on extension activation
	mcpManager.registerMemMachineServer().catch(error => {
		console.error('Failed to auto-register default MemMachine server:', error);
	});
}

// This method is called when your extension is deactivated
export function deactivate() {
	// Clean up MCP server connections
	const mcpManager = MCPServerManager.getInstance();
	const registeredServers = mcpManager.getRegisteredServers();
	
	// Unregister all MCP servers
	for (const server of registeredServers) {
		mcpManager.unregisterServer(server.name).catch(error => {
			console.error(`Failed to unregister MCP server ${server.name}:`, error);
		});
	}
	
	console.log('MemMachine extension deactivated - MCP servers unregistered');
}
