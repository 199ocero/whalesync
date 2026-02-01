"""
TUI Application for Polymarket Bot
Uses Textual to provide a real-time dashboard
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Grid
from textual.widgets import Header, Footer, Static, DataTable, Log, Button, Label, Digits
from textual.reactive import reactive
from textual.screen import Screen
import asyncio

from tui import widgets
from database import db
from engine import paper_trading
import config

class DashboardScreen(Screen):
    """Main dashboard screen"""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "toggle_theme", "Toggle Theme"),
        ("r", "refresh", "Force Refresh"),
        ("p", "pause_feed", "Pause/Resume Feed"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Grid(id="main_grid"):
            # Left Column: Strategy Status
            with Container(id="strategy_panel", classes="panel"):
                yield Label("STRATEGY STATUS", classes="panel_title")
                yield widgets.StrategyStatus("NegRisk Arb", "negrisk_arb", id="status_negrisk")
                yield widgets.StrategyStatus("Bond Scanner", "high_prob_bond", id="status_bond")
                yield widgets.StrategyStatus("Whale Copy", "whale_copy", id="status_whale")
                yield widgets.StrategyStatus("Temporal Arb", "temporal_arb", id="status_temporal")
                
                yield Static(classes="spacer")
                yield Label("GLOBAL STATS", classes="panel_title")
                yield widgets.GlobalStats(id="global_stats")

            # Middle Column: Activity Feed
            with Container(id="feed_panel", classes="panel"):
                yield Label("ACTIVITY FEED", classes="panel_title")
                yield Log(id="activity_log", highlight=True)

            # Right Column: Data Tables
            with Container(id="data_panel", classes="panel"):
                yield Label("OPEN POSITIONS", classes="panel_title")
                yield DataTable(id="positions_table")
                
                yield Static(classes="spacer")
                yield Label("DAILY P&L", classes="panel_title")
                yield widgets.PnLDisplay(id="pnl_display")
        
        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted"""
        # Register logger callback
        from tui.logger import logger
        logger.set_callback(self.on_log_message)
        
        # Send test message to verify activity feed is working
        self.on_log_message("🚀 Dashboard started - Activity feed is live!")
        self.on_log_message("Monitoring strategies and whale activity...")
        
        # Start background refresh tasks
        self.set_interval(config.DASHBOARD_REFRESH_INTERVAL, self.refresh_data)
        
        # Setup tables
        table = self.query_one("#positions_table", DataTable)
        table.add_columns("Market", "Side", "Size", "P&L")

    def on_log_message(self, message: str) -> None:
        """Handle incoming log message"""
        log = self.query_one("#activity_log", Log)
        log.write(message + "\n")  # Add newline for proper formatting

    async def refresh_data(self) -> None:
        """Refresh all data widgets"""
        # Trigger updates on widgets
        self.query_one("#global_stats", widgets.GlobalStats).update_stats()
        self.query_one("#pnl_display", widgets.PnLDisplay).update_pnl()
        await self.update_positions()

    async def update_positions(self) -> None:
        """Update open positions table"""
        table = self.query_one("#positions_table", DataTable)
        table.clear()
        
        trades = await db.get_open_trades()
        for trade in trades:
            # Color code based on P&L (simulated)
            market_name = trade["market_name"][:20] + "..."
            side = f"[{'green' if trade['side']=='YES' else 'red'}]{trade['side']}[/]"
            size = f"${trade['cost']:.2f}"
            
            # Simulated current pnl (just 0 for now as we don't have live market price here yet)
            pnl = "$0.00"
            
            table.add_row(market_name, side, size, pnl)
    
    def action_pause_feed(self) -> None:
        """Toggle pause/resume of activity feed"""
        from tui.logger import logger
        
        if logger.is_paused():
            logger.resume()
            log = self.query_one("#activity_log", Log)
            log.write("▶️  Activity feed resumed")
        else:
            log = self.query_one("#activity_log", Log)
            log.write("⏸️  Activity feed paused")
            logger.pause()

class SetupScreen(Screen):
    """First-run setup screen"""
    
    def compose(self) -> ComposeResult:
        yield Container(
            Label("Welcome to Polymarket Bot!", id="welcome_title"),
            Label("Please enter your starting paper trading fund (USD):"),
            # Placeholder for proper input - using Static for now as placeholder
            Label("Run with 'python main.py' to setup fund in CLI first!", classes="error"),
            Button("I have setup the fund", id="btn_done", variant="primary"),
            id="setup_dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_done":
            self.app.push_screen(DashboardScreen())

class PolymarketTUI(App):
    """Main TUI Application"""
    
    CSS_PATH = "style.tcss"
    TITLE = "Polymarket Trading Bot"
    
    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())

if __name__ == "__main__":
    app = PolymarketTUI()
    app.run()
