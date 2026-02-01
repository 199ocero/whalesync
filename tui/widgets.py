"""
TUI Widgets
Custom reusable widgets for the dashboard
"""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, Label, Digits
from textual.reactive import reactive
import asyncio
from database import db

class StrategyStatus(Container):
    """Widget to display status of a single strategy"""
    
    active = reactive(True)
    
    def __init__(self, name: str, strategy_id: str, **kwargs):
        super().__init__(**kwargs)
        self.strategy_name = name
        self.strategy_id = strategy_id
        
    def compose(self) -> ComposeResult:
        yield Label(self.strategy_name, classes="strategy-name")
        yield Label("●", classes="strategy-indicator")

    def watch_active(self, active: bool) -> None:
        self.remove_class("active")
        self.remove_class("inactive")
        
        if active:
            self.add_class("active")
            self.query_one(".strategy-indicator", Label).update("[green]●[/]")
        else:
            self.add_class("inactive")
            self.query_one(".strategy-indicator", Label).update("[red]●[/]")

class GlobalStats(Container):
    """Widget for global statistics (Balance, P&L)"""
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="stat-row"):
            yield Label("Balance:", classes="stat-label")
            yield Label("$0.00", id="val_balance", classes="stat-value")
        
        with Horizontal(classes="stat-row"):
            yield Label("All-Time P&L:", classes="stat-label")
            yield Label("$0.00", id="val_pnl", classes="stat-value")
            
        with Horizontal(classes="stat-row"):
            yield Label("Active Whales:", classes="stat-label")
            yield Label("0", id="val_whales", classes="stat-value")

    def update_stats(self) -> None:
        """Fetch updated stats from DB and update labels"""
        # This needs to be async, but Textual's on_interval isn't inherently async
        # We'll use asyncio.create_task to run the DB fetch
        asyncio.create_task(self._fetch_and_update())

    async def _fetch_and_update(self):
        fund = await db.get_paper_fund()
        if fund:
            balance = f"${fund['current_balance']:,.2f}"
            pnl_val = fund['total_profit'] - fund['total_loss']
            pnl = f"[green]${pnl_val:,.2f}[/]" if pnl_val >= 0 else f"[red]-${abs(pnl_val):,.2f}[/]"
            
            self.query_one("#val_balance", Label).update(balance)
            self.query_one("#val_pnl", Label).update(pnl)
            
        whales = await db.get_active_whales()
        self.query_one("#val_whales", Label).update(str(len(whales)))

class PnLDisplay(Container):
    """Widget to display P&L breakdown"""
    
    def compose(self) -> ComposeResult:
         with Horizontal(classes="stat-row"):
            yield Label("Today:", classes="stat-label")
            yield Label("$0.00", id="val_daily_pnl", classes="stat-value")

    def update_pnl(self) -> None:
        asyncio.create_task(self._fetch_pnl())
        
    async def _fetch_pnl(self):
        daily = await db.get_daily_pnl()
        if daily:
             val = daily['total_pnl']
             pnl = f"[green]${val:,.2f}[/]" if val >= 0 else f"[red]-${abs(val):,.2f}[/]"
             self.query_one("#val_daily_pnl", Label).update(pnl)
