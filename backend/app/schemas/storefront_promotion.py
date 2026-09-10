from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


PromotionMethod = Literal["AUTOMATIC", "CODE"]
PromotionKind = Literal["AMOUNT_OFF", "BUY_X_GET_Y"]
PromotionTargetType = Literal["COLLECTION", "PRODUCT", "ORDER", "SHIPPING"]
PromotionDiscountType = Literal["PERCENT", "FIXED", "FREE_SHIPPING"]
PromotionMinimumRequirement = Literal["NONE", "AMOUNT", "QUANTITY"]
PromotionCustomerEligibility = Literal["ALL", "NEW_CUSTOMERS", "RETURNING_CUSTOMERS"]
PromotionRewardTargetType = Literal["COLLECTION", "PRODUCT"]
PromotionGetDiscountType = Literal["PERCENT", "FIXED"]


class PromotionIn(BaseModel):
    storefront_id: UUID
    name: str = Field(min_length=2, max_length=120)
    method: PromotionMethod = "AUTOMATIC"
    code: str | None = Field(default=None, max_length=80)
    promotion_type: PromotionKind = "AMOUNT_OFF"
    target_type: PromotionTargetType
    collection_id: UUID | None = None
    published_product_id: UUID | None = None
    reward_target_type: PromotionRewardTargetType | None = None
    reward_collection_id: UUID | None = None
    reward_published_product_id: UUID | None = None
    buy_quantity: int = Field(default=1, gt=0, le=10_000)
    get_quantity: int = Field(default=1, gt=0, le=10_000)
    get_discount_type: PromotionGetDiscountType = "PERCENT"
    get_discount_value: float = Field(default=100, gt=0, le=100_000_000)
    discount_type: PromotionDiscountType = "PERCENT"
    discount_value: float | None = Field(default=None, ge=0)
    # Legacy clients still send this field. It is normalized into
    # discount_value before persistence.
    discount_percent: float | None = Field(default=None, gt=0, le=100)
    priority: int = Field(default=0, ge=0, le=1000)
    minimum_requirement: PromotionMinimumRequirement = "NONE"
    minimum_amount: float = Field(default=0, ge=0)
    minimum_quantity: int = Field(default=0, ge=0)
    usage_limit: int | None = Field(default=None, gt=0)
    once_per_customer: bool = False
    combines_with_product: bool = False
    combines_with_order: bool = False
    combines_with_shipping: bool = False
    customer_eligibility: PromotionCustomerEligibility = "ALL"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_configuration(self) -> "PromotionIn":
        if self.method == "CODE":
            self.code = (self.code or "").strip().upper() or None
            if not self.code:
                raise ValueError("Las promociones con código necesitan un código")
        else:
            self.code = None

        if self.promotion_type == "BUY_X_GET_Y":
            if self.target_type not in {"COLLECTION", "PRODUCT"}:
                raise ValueError("Compra X y lleva Y necesita productos o una colección como condición")
            if self.target_type == "COLLECTION" and self.collection_id is None:
                raise ValueError("Selecciona la colección que activa la promoción")
            if self.target_type == "PRODUCT" and self.published_product_id is None:
                raise ValueError("Selecciona el producto que activa la promoción")
            if self.reward_target_type is None:
                self.reward_target_type = self.target_type
            reward_count = int(self.reward_collection_id is not None) + int(self.reward_published_product_id is not None)
            if reward_count == 0:
                self.reward_collection_id = self.collection_id
                self.reward_published_product_id = self.published_product_id
            elif reward_count != 1:
                raise ValueError("Selecciona exactamente una colección o un producto como recompensa")
            if self.reward_target_type == "COLLECTION" and self.reward_collection_id is None:
                raise ValueError("La recompensa necesita una colección")
            if self.reward_target_type == "PRODUCT" and self.reward_published_product_id is None:
                raise ValueError("La recompensa necesita un producto")
            if self.get_discount_type == "PERCENT" and self.get_discount_value > 100:
                raise ValueError("El descuento de la recompensa no puede superar 100%")
            if self.get_discount_type == "FIXED" and self.get_discount_value <= 0:
                raise ValueError("El descuento fijo de la recompensa debe ser mayor que cero")
        elif self.target_type in {"ORDER", "SHIPPING"}:
            if self.collection_id is not None or self.published_product_id is not None:
                raise ValueError("Las promociones de pedido o envío no llevan un producto objetivo")
        else:
            target_count = int(self.collection_id is not None) + int(self.published_product_id is not None)
            if target_count != 1:
                raise ValueError("Selecciona exactamente una colección o un producto")
            if self.target_type == "COLLECTION" and self.collection_id is None:
                raise ValueError("Una promoción de colección necesita una colección")
            if self.target_type == "PRODUCT" and self.published_product_id is None:
                raise ValueError("Una promoción de producto necesita un producto")

        if self.target_type == "SHIPPING" and self.discount_type != "FREE_SHIPPING":
            raise ValueError("Una promoción de envío debe ser de envío gratis")
        if self.target_type != "SHIPPING" and self.discount_type == "FREE_SHIPPING":
            raise ValueError("El envío gratis solo aplica al objetivo de envío")

        if self.promotion_type == "BUY_X_GET_Y":
            self.discount_type = "PERCENT"
            self.discount_value = 100

        value = self.discount_value if self.discount_value is not None else self.discount_percent
        if value is None and self.discount_type == "FREE_SHIPPING":
            value = 0
        if value is None:
            raise ValueError("Indica el valor del descuento")
        if self.discount_type == "PERCENT" and not 0 < value <= 100:
            raise ValueError("El porcentaje debe estar entre 0,01 y 100")
        if self.discount_type == "FIXED" and value <= 0:
            raise ValueError("El descuento fijo debe ser mayor que cero")
        if self.discount_type == "FREE_SHIPPING":
            value = 0
        self.discount_value = value
        self.discount_percent = value if self.discount_type == "PERCENT" else None

        if self.minimum_requirement == "AMOUNT" and self.minimum_amount <= 0:
            raise ValueError("Indica un monto mínimo mayor que cero")
        if self.minimum_requirement == "QUANTITY" and self.minimum_quantity <= 0:
            raise ValueError("Indica una cantidad mínima mayor que cero")
        if self.starts_at and self.ends_at and self.starts_at > self.ends_at:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final")
        return self


class PromotionUpdate(BaseModel):
    storefront_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    method: PromotionMethod | None = None
    code: str | None = Field(default=None, max_length=80)
    promotion_type: PromotionKind | None = None
    target_type: PromotionTargetType | None = None
    collection_id: UUID | None = None
    published_product_id: UUID | None = None
    reward_target_type: PromotionRewardTargetType | None = None
    reward_collection_id: UUID | None = None
    reward_published_product_id: UUID | None = None
    buy_quantity: int | None = Field(default=None, gt=0, le=10_000)
    get_quantity: int | None = Field(default=None, gt=0, le=10_000)
    get_discount_type: PromotionGetDiscountType | None = None
    get_discount_value: float | None = Field(default=None, gt=0, le=100_000_000)
    discount_type: PromotionDiscountType | None = None
    discount_value: float | None = Field(default=None, ge=0)
    discount_percent: float | None = Field(default=None, gt=0, le=100)
    priority: int | None = Field(default=None, ge=0, le=1000)
    minimum_requirement: PromotionMinimumRequirement | None = None
    minimum_amount: float | None = Field(default=None, ge=0)
    minimum_quantity: int | None = Field(default=None, ge=0)
    usage_limit: int | None = Field(default=None, gt=0)
    once_per_customer: bool | None = None
    combines_with_product: bool | None = None
    combines_with_order: bool | None = None
    combines_with_shipping: bool | None = None
    customer_eligibility: PromotionCustomerEligibility | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool | None = None


class PromotionOut(BaseModel):
    id: UUID
    storefront_id: UUID
    name: str
    method: PromotionMethod
    code: str | None = None
    promotion_type: PromotionKind
    target_type: PromotionTargetType
    collection_id: UUID | None = None
    published_product_id: UUID | None = None
    collection_name: str | None = None
    product_name: str | None = None
    reward_target_type: PromotionRewardTargetType | None = None
    reward_collection_id: UUID | None = None
    reward_published_product_id: UUID | None = None
    reward_collection_name: str | None = None
    reward_product_name: str | None = None
    buy_quantity: int
    get_quantity: int
    get_discount_type: PromotionGetDiscountType
    get_discount_value: float
    target_label: str
    discount_type: PromotionDiscountType
    discount_value: float
    discount_percent: float | None = None
    priority: int
    minimum_requirement: PromotionMinimumRequirement
    minimum_amount: float
    minimum_quantity: int
    usage_limit: int | None = None
    usage_count: int
    once_per_customer: bool
    combines_with_product: bool
    combines_with_order: bool
    combines_with_shipping: bool
    customer_eligibility: PromotionCustomerEligibility
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
