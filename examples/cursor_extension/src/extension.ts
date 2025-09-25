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
		const success = await mcpManager.registerServer({
			name: MCP_NAME,
			url: MCP_URL,
			headers: {
				'Authorization': `Bearer ${AUTH_TOKEN}`
			}
		});

		if (success) {
			vscode.window.showInformationMessage(`MCP server '${MCP_NAME}' registered successfully!`);
		}
	});

	let unregisterMCPServerDisposable = vscode.commands.registerCommand('memmachine.unregisterMCPServer', async () => {
		const success = await mcpManager.unregisterServer(MCP_NAME);
		if (success) {
			vscode.window.showInformationMessage(`MCP server '${MCP_NAME}' unregistered successfully!`);
		}
	});


	context.subscriptions.push(
		showEpisodicMemoryDisposable, 
		refreshAllMemoriesDisposable,
		refreshEpisodicMemoryDisposable, 
		showProfileMemoryDisposable,
		refreshProfileMemoryDisposable,
		registerMCPServerDisposable,
		unregisterMCPServerDisposable,
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
