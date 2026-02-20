import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.sale import Sale
from app.models.return_order import ReturnOrder, ReturnOrderItem, ReturnStatus, ReturnType
from app.core.config import settings
import uuid

async def test_db():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get a delivered sale
        result = await session.execute(select(Sale).where(Sale.status == "DELIVERED"))
        sale = result.scalars().first()
        if not sale:
            result = await session.execute(select(Sale).where(Sale.status == "COMPLETED"))
            sale = result.scalars().first()
            
        if not sale:
            print("No DELIVERED/COMPLETED sale found in DB.")
            return

        print(f"Testing with sale {sale.id}")
        
        try:
            return_order = ReturnOrder(
                sale_id=sale.id,
                created_by=sale.user_id,
                return_type=ReturnType.PARTIAL,
                status=ReturnStatus.PENDING,
                company_id=sale.company_id,
                total_refund=100.0
            )
            session.add(return_order)
            await session.commit()
            
            # Re-fetch with exact eager loading used in endpoint
            from sqlalchemy.orm import selectinload
            from app.models.return_order import ReturnOrderItem
            from app.models.product import Product

            def _return_options():
                return [
                    selectinload(ReturnOrder.items).selectinload(ReturnOrderItem.product).options(
                        selectinload(Product.images),
                        selectinload(Product.variants),
                    ),
                    selectinload(ReturnOrder.creator),
                    selectinload(ReturnOrder.approver),
                ]

            result = await session.execute(
                select(ReturnOrder).options(*_return_options()).where(ReturnOrder.id == return_order.id)
            )
            ret = result.scalars().first()

            from app.schemas.return_order import ReturnOrderResponse
            # THIS is what fails in fastapi!
            try:
                out = ReturnOrderResponse.model_validate(ret)
                print("Serialization SUCCESS:")
            except Exception as e:
                import traceback
                print("PYDANTIC ERROR:")
                traceback.print_exc()

            print("Created return order ID:", return_order.id)
            await session.delete(ret)
            await session.commit()
        except Exception as e:
            print("DB ERROR:", type(e))
            print("EXCEPTION DETAILS:", str(e))

if __name__ == "__main__":
    asyncio.run(test_db())
