from typing import List, Optional
from pydantic import BaseModel
from datetime import date

class DashboardCard(BaseModel):
    title: str
    amount: str
    background: str
    border: str
    icon: str
    percentage: str
    color: str
    number: str

class RecentOrder(BaseModel):
    id: str  # Display ID (e.g. truncated UUID or reference)
    name: str # Product name or customer name? Dashboard shows product name in table.
    status: str
    status_type: str # 'text-success', etc.
    quantity: int
    amount: str

class TransactionHistory(BaseModel):
    background: str
    icon: str
    title: str
    time: str
    amount: str
    percentage: str

class ChartData(BaseModel):
    categories: List[str]
    series: List[dict] # {name: str, data: List[number]}

class DashboardStats(BaseModel):
    cards: List[DashboardCard]
    recent_orders: List[RecentOrder]
    transactions: List[TransactionHistory]
    monthly_sales: ChartData
    income_overview: ChartData
    sales_report: ChartData
