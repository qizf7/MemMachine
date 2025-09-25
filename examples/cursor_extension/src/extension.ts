// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import { EpisodicMemoryTreeProvider } from './episodicMemoryTreeProvider';
import { ProfileMemoryTreeProvider } from './profileMemoryTreeProvider';

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

	// Use the console to output diagnostic information (console.log) and errors (console.error)
	// This line of code will only be executed once when your extension is activated
	console.log('Congratulations, your extension "memmachine" is now active!');

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


	context.subscriptions.push(
		disposable, 
		showEpisodicMemoryDisposable, 
		refreshAllMemoriesDisposable,
		refreshEpisodicMemoryDisposable, 
		showProfileMemoryDisposable,
		refreshProfileMemoryDisposable
	);
}

// This method is called when your extension is deactivated
export function deactivate() {}
