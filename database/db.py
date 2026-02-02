"""
Database layer for Polymarket Multi-Strategy Trading Bot
SQLite schema and async operations using aiosqlite
"""

import aiosqlite
from datetime import datetime
from typing import Optional, Dict, List, Any
import config

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

async def init_database():
    """Initialize SQLite database with all required tables"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Paper fund table (single row)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_fund (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                starting_fund REAL NOT NULL,
                current_balance REAL NOT NULL,
                total_profit REAL DEFAULT 0,
                total_loss REAL DEFAULT 0,
                total_fees_paid REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL
            )
        """)
        
        # Paper trades table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id TEXT NOT NULL,
                market_id TEXT NOT NULL,
                market_name TEXT,
                asset TEXT,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                shares REAL NOT NULL,
                cost REAL NOT NULL,
                fee REAL DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                outcome TEXT,
                payout REAL,
                profit_or_loss REAL,
                arb_id TEXT,
                resolution_time TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        
        # Whales table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whales (
                wallet_address TEXT PRIMARY KEY,
                profit_7d REAL,
                total_trades INTEGER,
                win_rate REAL,
                last_trade_at TEXT,
                is_active INTEGER DEFAULT 1,
                cluster_id TEXT,
                discovered_at TEXT NOT NULL,
                last_checked_at TEXT NOT NULL
            )
        """)
        
        # Whale clusters table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whale_clusters (
                cluster_id TEXT PRIMARY KEY,
                wallet_addresses TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Whale trades table (historical tracking)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whale_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_address TEXT NOT NULL,
                market_id TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                shares REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (wallet_address) REFERENCES whales(wallet_address)
            )
        """)
        
        # Signals table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                side TEXT NOT NULL,
                whale_count INTEGER NOT NULL,
                confidence TEXT NOT NULL,
                price_at_signal REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Daily P&L table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_pnl (
                date TEXT PRIMARY KEY,
                negrisk_arb_pnl REAL DEFAULT 0,
                high_prob_bond_pnl REAL DEFAULT 0,
                whale_copy_pnl REAL DEFAULT 0,
                temporal_arb_pnl REAL DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0
            )
        """)
        
        await db.commit()

# ============================================================================
# PAPER FUND OPERATIONS
# ============================================================================

async def get_paper_fund() -> Optional[Dict[str, Any]]:
    """Get paper fund data"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM paper_fund WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_paper_fund(starting_fund: float) -> None:
    """Create initial paper fund"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO paper_fund (
                id, starting_fund, current_balance, created_at, last_updated_at
            ) VALUES (1, ?, ?, ?, ?)
        """, (starting_fund, starting_fund, now, now))
        await db.commit()

async def update_paper_fund_balance(
    new_balance: float,
    profit: float = 0,
    loss: float = 0,
    fee: float = 0,
    is_win: bool = False,
    is_loss: bool = False
) -> None:
    """Update paper fund after trade resolution"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            UPDATE paper_fund SET
                current_balance = ?,
                total_profit = total_profit + ?,
                total_loss = total_loss + ?,
                total_fees_paid = total_fees_paid + ?,
                total_trades = total_trades + 1,
                winning_trades = winning_trades + ?,
                losing_trades = losing_trades + ?,
                last_updated_at = ?
            WHERE id = 1
        """, (new_balance, profit, loss, fee, 1 if is_win else 0, 1 if is_loss else 0, now))
        await db.commit()

async def get_daily_spend() -> float:
    """Get total amount spent on trades today"""
    today = datetime.utcnow().date().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT SUM(cost + fee) as total_spend
            FROM paper_trades
            WHERE DATE(created_at) = ?
        """, (today,))
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0.0


# ============================================================================
# PAPER TRADES OPERATIONS
# ============================================================================

async def create_paper_trade(
    strategy_id: str,
    market_id: str,
    market_name: str,
    side: str,
    price: float,
    shares: float,
    cost: float,
    fee: float = 0,
    arb_id: Optional[str] = None,
    asset: Optional[str] = None,
    resolution_time: Optional[str] = None
) -> int:
    """Create a new paper trade"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO paper_trades (
                strategy_id, market_id, market_name, asset, side, price, shares,
                cost, fee, arb_id, resolution_time, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (strategy_id, market_id, market_name, asset, side, price, shares, cost, fee, arb_id, resolution_time, now))
        await db.commit()
        return cursor.lastrowid

async def get_open_trades() -> List[Dict[str, Any]]:
    """Get all open trades"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM paper_trades WHERE status = 'OPEN'"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def resolve_trade(
    trade_id: int,
    outcome: str,
    payout: float,
    profit_or_loss: float
) -> None:
    """Mark trade as resolved"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            UPDATE paper_trades SET
                status = 'RESOLVED',
                outcome = ?,
                payout = ?,
                profit_or_loss = ?,
                resolved_at = ?
            WHERE id = ?
        """, (outcome, payout, profit_or_loss, now, trade_id))
        await db.commit()

async def get_recent_trades(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent trades for TUI display"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM paper_trades
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

# ============================================================================
# WHALE OPERATIONS
# ============================================================================

async def upsert_whale(
    wallet_address: str,
    profit_7d: float,
    total_trades: int,
    win_rate: float,
    last_trade_at: str,
    cluster_id: Optional[str] = None
) -> None:
    """Insert or update whale data"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO whales (
                wallet_address, profit_7d, total_trades, win_rate,
                last_trade_at, cluster_id, discovered_at, last_checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(wallet_address) DO UPDATE SET
                profit_7d = excluded.profit_7d,
                total_trades = excluded.total_trades,
                win_rate = excluded.win_rate,
                last_trade_at = excluded.last_trade_at,
                cluster_id = excluded.cluster_id,
                last_checked_at = excluded.last_checked_at
        """, (wallet_address, profit_7d, total_trades, win_rate, last_trade_at, cluster_id, now, now))
        await db.commit()

async def get_active_whales() -> List[Dict[str, Any]]:
    """Get all active whales"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM whales WHERE is_active = 1 ORDER BY profit_7d DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def log_whale_trade(
    wallet_address: str,
    market_id: str,
    side: str,
    price: float,
    shares: float
) -> bool:
    """Log a whale trade with duplicate detection. Returns True if logged, False if duplicate."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Check for duplicate (same wallet, market, side within last 5 minutes)
        cursor = await db.execute("""
            SELECT id FROM whale_trades 
            WHERE wallet_address = ? 
            AND market_id = ? 
            AND side = ?
            AND datetime(timestamp) > datetime('now', '-5 minutes')
        """, (wallet_address, market_id, side))
        
        existing = await cursor.fetchone()
        if existing:
            return False  # Duplicate
        
        # Log new trade
        await db.execute("""
            INSERT INTO whale_trades (
                wallet_address, market_id, side, price, shares, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (wallet_address, market_id, side, price, shares, now))
        await db.commit()
        return True  # Logged successfully

async def get_whale_trades_for_market(market_id: str, since: datetime) -> List[Dict[str, Any]]:
    """Get all whale trades for a specific market since a given time"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT wallet_address, market_id, side, price, shares, timestamp
            FROM whale_trades
            WHERE market_id = ?
            AND datetime(timestamp) > datetime(?)
            ORDER BY timestamp DESC
        """, (market_id, since.isoformat()))
        
        rows = await cursor.fetchall()
        return [
            {
                "wallet_address": row[0],
                "market_id": row[1],
                "side": row[2],
                "price": row[3],
                "shares": row[4],
                "timestamp": row[5]
            }
            for row in rows
        ]

# ============================================================================
# SIGNAL OPERATIONS
# ============================================================================

async def create_signal(
    market_id: str,
    side: str,
    whale_count: int,
    confidence: str,
    price_at_signal: float
) -> int:
    """Create a new signal"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO signals (
                market_id, side, whale_count, confidence, price_at_signal, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (market_id, side, whale_count, confidence, price_at_signal, now))
        await db.commit()
        return cursor.lastrowid

# ============================================================================
# DAILY P&L OPERATIONS
# ============================================================================

async def update_daily_pnl(strategy_id: str, pnl: float) -> None:
    """Update daily P&L for a strategy"""
    today = datetime.utcnow().date().isoformat()
    
    # Map strategy_id to column name
    strategy_columns = {
        "NEGRISK_ARB": "negrisk_arb_pnl",
        "HIGH_PROB_BOND": "high_prob_bond_pnl",
        "WHALE_COPY": "whale_copy_pnl",
        "TEMPORAL_ARB": "temporal_arb_pnl"
    }
    
    column = strategy_columns.get(strategy_id)
    if not column:
        return
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Insert or update
        await db.execute(f"""
            INSERT INTO daily_pnl (date, {column}, total_pnl, total_trades)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(date) DO UPDATE SET
                {column} = {column} + excluded.{column},
                total_pnl = total_pnl + excluded.total_pnl,
                total_trades = total_trades + 1
        """, (today, pnl, pnl))
        await db.commit()

async def get_daily_pnl(date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get P&L for a specific date (defaults to today)"""
    if not date:
        date = datetime.utcnow().date().isoformat()
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM daily_pnl WHERE date = ?", (date,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
