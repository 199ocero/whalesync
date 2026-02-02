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
    """Widget to display P&L breakdown by strategy"""
    
    def compose(self) -> ComposeResult:
        # Vertical layout with separate labels
        yield Static("Total: $0.00", id="pnl_total", classes="pnl-line")
        yield Static("NR: $0 | Bonds: $0", id="pnl_line1", classes="pnl-line-small")
        yield Static("Whale: $0 | Temp: $0", id="pnl_line2", classes="pnl-line-small")

    def update_pnl(self) -> None:
        asyncio.create_task(self._fetch_pnl())
        
    async def _fetch_pnl(self):
        daily = await db.get_daily_pnl()
        if daily:
            # Format values
            total = daily['total_pnl']
            negrisk = daily.get('negrisk_arb_pnl', 0)
            bond = daily.get('high_prob_bond_pnl', 0)
            whale = daily.get('whale_copy_pnl', 0)
            temporal = daily.get('temporal_arb_pnl', 0)
            
            # Color code based on positive/negative
            def fmt(val):
                if val >= 0:
                    return f"[green]${val:.2f}[/]"
                else:
                    return f"[red]-${abs(val):.2f}[/]"
            
            # Update displays across 3 lines
            self.query_one("#pnl_total", Static).update(f"Total: {fmt(total)}")
            self.query_one("#pnl_line1", Static).update(f"NR: {fmt(negrisk)} | Bonds: {fmt(bond)}")
            self.query_one("#pnl_line2", Static).update(f"Whale: {fmt(whale)} | Temp: {fmt(temporal)}")
        else:
            # No data yet
            self.query_one("#pnl_total", Static).update("Total: $0.00")
            self.query_one("#pnl_line1", Static).update("NR: $0 | Bonds: $0")
            self.query_one("#pnl_line2", Static).update("Whale: $0 | Temp: $0")


