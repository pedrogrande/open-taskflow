# Add and manage MCP servers in VS Code

Source: <https://code.visualstudio.com/raw/docs/agent-customization/mcp-servers.md>
As at 5th June 2026

For background on how MCP fits into the AI customization framework, see [Customization concepts](/docs/agents/concepts/customization.md#mcp) and [Tools concepts](/docs/agents/concepts/tools.md).

This article covers how to add, configure, and manage MCP servers. To learn about using tools in chat, see [Use tools with agents](/docs/agents/agent-tools.md).

> [!TIP]
> Use the [Agent Customizations editor](/docs/agent-customization/overview.md#agent-customizations-editor) (Preview) to discover, create, and manage all your agent customizations in one place. Run **Chat: Open Customizations** from the Command Palette.

## Quickstart: use an MCP server in chat

Follow these steps to install an MCP server and use its tools in chat. This example uses the [Playwright](https://github.com/microsoft/playwright-mcp) MCP server to interact with web pages through a browser.

1. Open the Extensions view (`kb(workbench.view.extensions)`) and enter `@mcp playwright` in the search field.

1. Select **Install** to install the Playwright MCP server in your user profile.

1. When prompted, confirm that you trust the server to start it. VS Code discovers the server's tools and makes them available in chat.

1. Open the Chat view (`kb(workbench.action.chat.open)`) and enter a prompt that uses the Playwright tools. For example:

    ```prompt
    Go to code.visualstudio.com, decline the cookie banner, and give me a screenshot of the homepage.
    ```

    VS Code invokes the Playwright tools to open the page in a browser, and take a screenshot. You might be asked to confirm each tool invocation.

> [!TIP]
> Select the **Configure Tools** button in the chat input to see all available tools for the Playwright MCP server and toggle specific tools on or off.

## Add an MCP server

To install an MCP server from the MCP server gallery:

1. Open the Extensions view (`kb(workbench.view.extensions)`) and enter `@mcp` in the search field. This shows the list of available MCP servers in the gallery.

1. You can install an MCP server in your user profile or in your workspace:

    * To install in your user profile, select **Install**.

    * To install in your workspace, right-click the MCP server and select **Install in Workspace**. This updates the `.vscode/mcp.json` file in your workspace.

1. To view the MCP server details, select the MCP server in the list to open the details page.

> [!CAUTION]
> Local MCP servers can run arbitrary code on your machine. Only add servers from [trusted sources](#mcp-server-trust), and review the publisher and server configuration before starting it. Read the [Security documentation](/docs/agents/security.md) for using AI in VS Code to understand the implications.

### Configure the `mcp.json` file

You can manually configure MCP servers by editing the `mcp.json` file. There are two locations for this file:

* **Workspace**: create or open `.vscode/mcp.json` in your project. Include this file in source control to share MCP server configurations with your team.
* **User profile**: run the **MCP: Open User Configuration** command to open the `mcp.json` file in your [user profile](/docs/configure/profiles.md) folder. Servers configured here are available across all your workspaces. When you use multiple profiles, each profile can have its own MCP server configuration.

You can also run **MCP: Add Server** in the Command Palette (`kb(workbench.action.showCommands)`) to add a server through a guided flow, choosing either **Workspace** or **Global** as the target.

> [!IMPORTANT]
> Avoid hardcoding sensitive information like API keys. Use [input variables](/docs/agents/reference/mcp-configuration.md#input-variables-for-sensitive-data) or environment files instead.

The following example shows an `mcp.json` file that configures a remote MCP server and a local MCP server:

```json
{
    "servers": {
        "github": {
            "type": "http",
            "url": "https://api.githubcopilot.com/mcp"
        },
        "playwright": {
            "command": "npx",
            "args": ["-y", "@microsoft/mcp-server-playwright"]
        }
    }
}
```

VS Code provides IntelliSense for the configuration file. For the full configuration schema and field reference, see the [MCP configuration reference](/docs/agents/reference/mcp-configuration.md).

> [!NOTE]
> MCP servers run wherever they are configured. Servers in your user profile run locally. If you're connected to a [remote](/docs/remote/remote-overview.md) and want a server to run on the remote machine, define it in the workspace settings or remote user settings (**MCP: Open Remote User Configuration**).

### Other options to add an MCP server

Install an MCP server from the command line

You can also use the VS Code command-line interface to add an MCP server to your user profile or to a workspace.

To add an MCP server to your user profile, use the `--add-mcp` VS Code command line option, and provide the JSON server configuration in the form `{\"name\":\"server-name\",\"command\":...}`.

```bash
code --add-mcp "{\"name\":\"my-server\",\"command\": \"uvx\",\"args\": [\"mcp-server-fetch\"]}"
```

## Other MCP capabilities

Beyond tools, MCP servers can provide other capabilities:

| Capability | Description | How to use |
|------------|-------------|------------|
| **Resources** | Access data from MCP servers as context in your prompts, such as files, database tables, or API responses. Resources provide read-only context that you attach to a chat request. | In the Chat view, select **Add Context** > **MCP Resources**. You can also use the **MCP: Browse Resources** command. |
| **Prompts** | Use preconfigured prompt templates from MCP servers to standardize common tasks. Each MCP server can expose its own set of prompts tailored to its capabilities. | Type `/<MCP server>.<prompt>` in the chat input. |
| **MCP Apps** | Get interactive UI components like forms, visualizations, and drag-and-drop lists rendered directly in chat. MCP Apps enable richer interactions beyond text responses. Learn more in the [MCP Apps blog post](https://code.visualstudio.com/blogs/2026/01/26/mcp-apps-support). | MCP Apps appear inline when an MCP server supports them. |

## Automatically start MCP servers

When you add an MCP server or change its configuration, VS Code needs to (re)start the server to discover the tools it provides.

You can configure VS Code to automatically restart the MCP server when configuration changes are detected by using the `setting(chat.mcp.autoStart)` setting (Experimental).

## MCP server trust

When you add an MCP server to your workspace or change its configuration, you need to confirm that you trust the server and its capabilities before starting it. VS Code shows a dialog to confirm that you trust the server when you start a server for the first time. In the dialog, select the link to the MCP server to review its configuration.

![Screenshot showing the MCP server trust prompt.](images/mcp-servers/mcp-server-trust-dialog.png)

If you don't trust the MCP server, it will not be started, and chat requests will continue without using the tools provided by the server.

You can reset trust for your MCP servers by running the **MCP: Reset Trust** command from the Command Palette.

> [!WARNING]
> If you start the MCP server directly from the `mcp.json` file, you will not be prompted to trust the server configuration.

## Synchronize MCP configuration across devices

With [Settings Sync](/docs/configure/settings-sync.md) enabled, you can synchronize settings and configurations across devices, including MCP server configurations. This enables you to maintain a consistent development environment and access the same MCP servers on all your devices.

To synchronize MCP server configuration with Settings Sync:

1. Run the **Settings Sync: Configure** command from the Command Palette

1. Enable the **MCP Servers** option in the list of synchronized configurations

## Troubleshoot and debug MCP servers

### MCP output log

When VS Code encounters an issue with an MCP server, it shows an error indicator in the Chat view.

![MCP Server Error](images/mcp-servers/mcp-error-loading-tool.png)

Select the error notification in the Chat view, and then select the **Show Output** option to view the server logs. Alternatively, run **MCP: List Servers** from the Command Palette, select the server, and then choose **Show Output**.

![MCP Server Error Output](images/mcp-servers/mcp-server-error-output.png)

## Frequently asked questions

<details>
<summary>The MCP server is not starting when using Docker</summary>

Verify that the command arguments are correct and that the container is not running in detached mode (`-d` option). You can also check the MCP server output for any error messages (see [Troubleshooting](#troubleshoot-and-debug-mcp-servers)).

</details>

## Related resources

* [MCP configuration reference](/docs/agents/reference/mcp-configuration.md)
* [Use tools with agents](/docs/agents/agent-tools.md)
* [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
* [MCP Apps support in VS Code](https://code.visualstudio.com/blogs/2026/01/26/mcp-apps-support)
* [Discover and manage agent plugins](/docs/agent-customization/agent-plugins.md), including [MCP servers in plugins](/docs/agent-customization/agent-plugins.md#mcp-servers-in-plugins)
