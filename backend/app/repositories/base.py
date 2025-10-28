"""
Repository基础类
定义通用的数据访问接口和方法
"""

from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.sql.functions import count as func_count
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.log_utils import get_logger
from app.core.log_messages import log_messages
from app.utils.id_utils import generate_uuid

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

logger = get_logger(__name__)


class BaseRepository(ABC):
    """Repository基础类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @property
    @abstractmethod
    def model(self) -> Type[ModelType]:
        """返回Repository对应的模型类"""

    async def get_by_id(self, record_id: str) -> Optional[ModelType]:
        """根据ID获取单个记录"""
        try:
            logger.info(log_messages.DB_QUERY_START,
                       operation_name="get_by_id",
                       record_id=record_id,
                       model_name=self.model.__name__)

            query = select(self.model).filter(self.model.id == record_id)
            result = await self.db.execute(query)
            record = result.scalars().first()

            if record:
                logger.info(log_messages.DB_QUERY_SUCCESS,
                           operation_name="get_by_id",
                           record_id=record_id,
                           model_name=self.model.__name__)
            else:
                logger.warning("记录不存在",
                             operation_name="get_by_id",
                             record_id=record_id,
                             model_name=self.model.__name__)

            return record

        except Exception as e:
            logger.error(log_messages.DB_QUERY_FAILED,
                       operation_name="get_by_id",
                       record_id=record_id,
                       model_name=self.model.__name__,
                       exception=e)
            raise

    async def create(self, **kwargs) -> ModelType:
        """创建新记录"""
        try:
            logger.info(log_messages.DB_UPDATE_START,
                       operation_name="create",
                       model_name=self.model.__name__,
                       kwargs=kwargs)

            # 如果模型有id字段但kwargs中没有提供id，自动生成UUID
            if hasattr(self.model, 'id') and 'id' not in kwargs:
                kwargs['id'] = generate_uuid()

            instance = self.model(**kwargs)
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)

            logger.info(log_messages.DB_UPDATE_SUCCESS,
                       operation_name="create",
                       model_name=self.model.__name__,
                       record_id=instance.id)

            return instance

        except Exception as e:
            await self.db.rollback()
            logger.error(log_messages.DB_UPDATE_FAILED,
                       operation_name="create",
                       model_name=self.model.__name__,
                       exception=e)
            raise

    async def update(
        self, record_id: str, **kwargs
    ) -> Optional[ModelType]:
        """更新记录"""
        try:
            logger.info(log_messages.DB_UPDATE_START,
                       operation_name="update",
                       record_id=record_id,
                       model_name=self.model.__name__,
                       update_fields=list(kwargs.keys()))

            instance = await self.get_by_id(record_id)
            if not instance:
                logger.warning("更新失败：记录不存在",
                             operation_name="update",
                             record_id=record_id,
                             model_name=self.model.__name__)
                return None

            # 记录更新前的值用于调试
            changed_fields = {}
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    old_value = getattr(instance, key)
                    if old_value != value:
                        changed_fields[key] = {"old": old_value, "new": value}
                    setattr(instance, key, value)

            await self.db.commit()
            await self.db.refresh(instance)

            logger.info(log_messages.DB_UPDATE_SUCCESS,
                       operation_name="update",
                       record_id=record_id,
                       model_name=self.model.__name__,
                       changed_fields=changed_fields)

            return instance

        except Exception as e:
            await self.db.rollback()
            logger.error(log_messages.DB_UPDATE_FAILED,
                       operation_name="update",
                       record_id=record_id,
                       model_name=self.model.__name__,
                       exception=e)
            raise

    async def delete(self, record_id: str) -> bool:
        """删除记录"""
        try:
            logger.info(log_messages.DB_UPDATE_START,
                       operation_name="delete",
                       record_id=record_id,
                       model_name=self.model.__name__)

            instance = await self.get_by_id(record_id)
            if not instance:
                logger.warning("删除失败：记录不存在",
                             operation_name="delete",
                             record_id=record_id,
                             model_name=self.model.__name__)
                return False

            await self.db.delete(instance)
            await self.db.commit()

            logger.info(log_messages.DB_UPDATE_SUCCESS,
                       operation_name="delete",
                       record_id=record_id,
                       model_name=self.model.__name__)

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(log_messages.DB_UPDATE_FAILED,
                       operation_name="delete",
                       record_id=record_id,
                       model_name=self.model.__name__,
                       exception=e)
            raise

    async def count(self, **filters) -> int:
        """统计记录数量"""
        try:
            logger.info(log_messages.DB_QUERY_START,
                       operation_name="count",
                       model_name=self.model.__name__,
                       filters=filters)

            query = select(func_count())

            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

            result = await self.db.execute(query)
            count = result.scalar() or 0

            logger.info(log_messages.DB_QUERY_SUCCESS,
                       operation_name="count",
                       model_name=self.model.__name__,
                       count=count)

            return count

        except Exception as e:
            logger.error(log_messages.DB_QUERY_FAILED,
                       operation_name="count",
                       model_name=self.model.__name__,
                       exception=e)
            raise
