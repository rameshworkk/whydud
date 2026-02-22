"""Scrapy item pipelines for data normalization and persistence."""


class ValidationPipeline:
    """Validate required fields before storing."""
    
    def process_item(self, item, spider):
        # TODO Sprint 2 Week 4
        return item


class NormalizationPipeline:
    """Clean titles, normalize specs and units, classify categories."""
    
    def process_item(self, item, spider):
        # TODO Sprint 2 Week 4
        return item


class DeduplicationPipeline:
    """Fuzzy product matching — merge into canonical products."""
    
    def process_item(self, item, spider):
        # TODO Sprint 2 Week 5
        return item


class PersistencePipeline:
    """Write normalized items to PostgreSQL."""
    
    def process_item(self, item, spider):
        # TODO Sprint 2 Week 4
        return item


class MeilisearchIndexPipeline:
    """Push updated products to Meilisearch after persistence."""
    
    def process_item(self, item, spider):
        # TODO Sprint 2 Week 4
        return item
