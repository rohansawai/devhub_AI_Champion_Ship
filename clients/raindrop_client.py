"""
Raindrop Client.
Unified interface for all Raindrop Smart Components.

This module provides managers for:
- SmartBuckets: RAG-ready document storage
- SmartSQL: Structured data queries
- SmartMemory: Persistent context storage
- SmartInference: LLM inference via Cerebras
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import time
import json
import httpx

from config.settings import settings


class RaindropError(Exception):
    """Exception raised for Raindrop API errors."""
    pass


class BaseManager(ABC):
    """Base class for Raindrop component managers."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the component. Returns True if successful."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


class BucketsManager(BaseManager):
    """
    Manager for SmartBuckets operations.
    
    SmartBuckets provides RAG-ready document storage with:
    - Automatic chunking and indexing
    - Semantic search capabilities
    - Metadata filtering
    
    Usage:
        manager = BucketsManager(api_key)
        manager.initialize()
        manager.store("air-readings", data, metadata={"city": "Tokyo"})
        results = manager.search("air-readings", "air quality in Tokyo")
    """
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._buckets: Dict[str, List[Dict]] = {}  # In-memory storage for now
    
    def initialize(self) -> bool:
        """Initialize SmartBuckets connection."""
        # TODO: Initialize via Raindrop MCP server
        # For now, we use in-memory storage
        self._initialized = True
        print("[SmartBuckets] Initialized (in-memory mode)")
        return True
    
    def store(
        self,
        bucket_name: str,
        data: Any,
        metadata: Dict = None,
        doc_id: str = None,
    ) -> str:
        """
        Store data in a SmartBucket.
        
        Args:
            bucket_name: Name of the bucket
            data: Data to store (will be JSON serialized)
            metadata: Optional metadata for filtering
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        if bucket_name not in self._buckets:
            self._buckets[bucket_name] = []
        
        doc_id = doc_id or f"doc_{len(self._buckets[bucket_name])}"
        
        document = {
            "id": doc_id,
            "data": data if isinstance(data, dict) else {"content": str(data)},
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        
        self._buckets[bucket_name].append(document)
        
        if settings.debug:
            print(f"[SmartBuckets] Stored doc '{doc_id}' in '{bucket_name}'")
        
        return doc_id
    
    def search(
        self,
        bucket_name: str,
        query: str,
        limit: int = 10,
        metadata_filter: Dict = None,
    ) -> List[Dict]:
        """
        Search a bucket using semantic similarity.
        
        Args:
            bucket_name: Name of the bucket to search
            query: Search query
            limit: Maximum number of results
            metadata_filter: Optional metadata filter
            
        Returns:
            List of matching documents
        """
        if bucket_name not in self._buckets:
            return []
        
        # TODO: Implement actual semantic search via Raindrop
        # For now, simple keyword matching
        results = []
        query_lower = query.lower()
        
        for doc in self._buckets[bucket_name]:
            # Simple keyword matching
            doc_str = json.dumps(doc["data"]).lower()
            if query_lower in doc_str or any(
                word in doc_str for word in query_lower.split()
            ):
                # Apply metadata filter if provided
                if metadata_filter:
                    if all(
                        doc["metadata"].get(k) == v
                        for k, v in metadata_filter.items()
                    ):
                        results.append(doc)
                else:
                    results.append(doc)
        
        return results[:limit]
    
    def get(self, bucket_name: str, doc_id: str) -> Optional[Dict]:
        """Get a specific document by ID."""
        if bucket_name not in self._buckets:
            return None
        
        for doc in self._buckets[bucket_name]:
            if doc["id"] == doc_id:
                return doc
        
        return None
    
    def delete(self, bucket_name: str, doc_id: str) -> bool:
        """Delete a document by ID."""
        if bucket_name not in self._buckets:
            return False
        
        self._buckets[bucket_name] = [
            doc for doc in self._buckets[bucket_name] if doc["id"] != doc_id
        ]
        return True
    
    def list_buckets(self) -> List[str]:
        """List all bucket names."""
        return list(self._buckets.keys())
    
    def clear_bucket(self, bucket_name: str) -> bool:
        """Clear all documents from a bucket."""
        if bucket_name in self._buckets:
            self._buckets[bucket_name] = []
            return True
        return False


class SQLManager(BaseManager):
    """
    Manager for SmartSQL operations.
    
    SmartSQL provides structured data storage with:
    - SQL-like queries
    - Automatic schema inference
    - Fast aggregations
    
    Usage:
        manager = SQLManager(api_key)
        manager.initialize()
        manager.insert("readings", {"city": "Tokyo", "pm25": 45.5})
        results = manager.execute("SELECT * FROM readings WHERE city = 'Tokyo'")
    """
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._tables: Dict[str, List[Dict]] = {}
    
    def initialize(self) -> bool:
        """Initialize SmartSQL connection."""
        # TODO: Initialize via Raindrop MCP server
        self._initialized = True
        print("[SmartSQL] Initialized (in-memory mode)")
        return True
    
    def create_table(self, table: str, schema: Dict = None) -> bool:
        """
        Create a table.
        
        Args:
            table: Table name
            schema: Optional schema definition (not enforced in mock)
            
        Returns:
            True if successful
        """
        if table not in self._tables:
            self._tables[table] = []
            if settings.debug:
                print(f"[SmartSQL] Created table '{table}'")
        return True
    
    def insert(self, table: str, data: Dict) -> bool:
        """
        Insert a row into a table.
        
        Args:
            table: Table name
            data: Row data as dictionary
            
        Returns:
            True if successful
        """
        if table not in self._tables:
            self._tables[table] = []
        
        # Add auto-generated ID if not present
        if "id" not in data:
            data["id"] = len(self._tables[table]) + 1
        
        self._tables[table].append(data.copy())
        
        if settings.debug:
            print(f"[SmartSQL] Inserted row into '{table}'")
        
        return True
    
    def execute(self, query: str, params: Dict = None) -> List[Dict]:
        """
        Execute a SQL-like query.
        
        Note: This is a simplified mock implementation.
        Real implementation would use Raindrop's SmartSQL.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of matching rows
        """
        # TODO: Implement actual SQL parsing via Raindrop
        # For now, simple pattern matching
        
        query_lower = query.lower()
        
        # Extract table name (simplified)
        if "from" in query_lower:
            parts = query_lower.split("from")
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                table = table_part.strip()
                
                if table in self._tables:
                    results = self._tables[table].copy()
                    
                    # Simple WHERE clause handling
                    if "where" in query_lower and params:
                        filtered = []
                        for row in results:
                            match = True
                            for key, value in params.items():
                                if row.get(key) != value:
                                    match = False
                                    break
                            if match:
                                filtered.append(row)
                        results = filtered
                    
                    # Simple LIMIT handling
                    if "limit" in query_lower:
                        try:
                            limit_idx = query_lower.index("limit")
                            limit_str = query_lower[limit_idx:].split()[1]
                            limit = int(limit_str)
                            results = results[:limit]
                        except (ValueError, IndexError):
                            pass
                    
                    return results
        
        return []
    
    def select(
        self,
        table: str,
        where: Dict = None,
        order_by: str = None,
        limit: int = None,
    ) -> List[Dict]:
        """
        Simplified select operation.
        
        Args:
            table: Table name
            where: Filter conditions
            order_by: Column to sort by
            limit: Maximum results
            
        Returns:
            List of matching rows
        """
        if table not in self._tables:
            return []
        
        results = self._tables[table].copy()
        
        # Apply WHERE filter
        if where:
            results = [
                row for row in results
                if all(row.get(k) == v for k, v in where.items())
            ]
        
        # Apply ORDER BY
        if order_by:
            reverse = order_by.startswith("-")
            key = order_by.lstrip("-")
            results.sort(key=lambda x: x.get(key, ""), reverse=reverse)
        
        # Apply LIMIT
        if limit:
            results = results[:limit]
        
        return results
    
    def update(self, table: str, where: Dict, data: Dict) -> int:
        """
        Update rows matching conditions.
        
        Returns:
            Number of rows updated
        """
        if table not in self._tables:
            return 0
        
        count = 0
        for row in self._tables[table]:
            if all(row.get(k) == v for k, v in where.items()):
                row.update(data)
                count += 1
        
        return count
    
    def delete_rows(self, table: str, where: Dict) -> int:
        """
        Delete rows matching conditions.
        
        Returns:
            Number of rows deleted
        """
        if table not in self._tables:
            return 0
        
        original_count = len(self._tables[table])
        self._tables[table] = [
            row for row in self._tables[table]
            if not all(row.get(k) == v for k, v in where.items())
        ]
        
        return original_count - len(self._tables[table])
    
    def list_tables(self) -> List[str]:
        """List all table names."""
        return list(self._tables.keys())


class MemoryManager(BaseManager):
    """
    Manager for SmartMemory operations.
    
    SmartMemory provides persistent context storage with:
    - User-scoped memories
    - Automatic context retrieval
    - Session management
    
    Usage:
        manager = MemoryManager(api_key)
        manager.initialize()
        manager.store("preferences", {"theme": "dark"}, user_id="user1")
        prefs = manager.retrieve("preferences", user_id="user1")
    """
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self._memory: Dict[str, Any] = {}  # Key format: "{user_id}:{key}"
    
    def initialize(self) -> bool:
        """Initialize SmartMemory connection."""
        # TODO: Initialize via Raindrop MCP server
        self._initialized = True
        print("[SmartMemory] Initialized (in-memory mode)")
        return True
    
    def store(
        self,
        key: str,
        value: Any,
        user_id: str = "default",
        ttl_seconds: int = None,
    ) -> bool:
        """
        Store a memory for a user.
        
        Args:
            key: Memory key
            value: Value to store (any JSON-serializable type)
            user_id: User identifier
            ttl_seconds: Optional time-to-live (not implemented in mock)
            
        Returns:
            True if successful
        """
        memory_key = f"{user_id}:{key}"
        self._memory[memory_key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl_seconds,
        }
        
        if settings.debug:
            print(f"[SmartMemory] Stored '{key}' for user '{user_id}'")
        
        return True
    
    def retrieve(self, key: str, user_id: str = "default") -> Optional[Any]:
        """
        Retrieve a memory.
        
        Args:
            key: Memory key
            user_id: User identifier
            
        Returns:
            Stored value or None if not found
        """
        memory_key = f"{user_id}:{key}"
        entry = self._memory.get(memory_key)
        
        if entry:
            # TODO: Check TTL expiration
            return entry["value"]
        
        return None
    
    def delete(self, key: str, user_id: str = "default") -> bool:
        """
        Delete a memory.
        
        Args:
            key: Memory key
            user_id: User identifier
            
        Returns:
            True if deleted, False if not found
        """
        memory_key = f"{user_id}:{key}"
        if memory_key in self._memory:
            del self._memory[memory_key]
            return True
        return False
    
    def get_context(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get all context for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of all memories for the user
        """
        prefix = f"{user_id}:"
        return {
            key.replace(prefix, ""): entry["value"]
            for key, entry in self._memory.items()
            if key.startswith(prefix)
        }
    
    def clear_user(self, user_id: str) -> int:
        """
        Clear all memories for a user.
        
        Returns:
            Number of memories cleared
        """
        prefix = f"{user_id}:"
        keys_to_delete = [k for k in self._memory.keys() if k.startswith(prefix)]
        
        for key in keys_to_delete:
            del self._memory[key]
        
        return len(keys_to_delete)
    
    def list_keys(self, user_id: str = "default") -> List[str]:
        """List all memory keys for a user."""
        prefix = f"{user_id}:"
        return [
            key.replace(prefix, "")
            for key in self._memory.keys()
            if key.startswith(prefix)
        ]


class InferenceManager(BaseManager):
    """
    Manager for SmartInference operations via Cerebras.
    
    SmartInference provides ultra-low latency LLM inference with:
    - Sub-second response times
    - Multiple model support
    - Streaming capabilities
    
    Usage:
        manager = InferenceManager(api_key, cerebras_api_key)
        manager.initialize()
        result = manager.query("What is the air quality in Tokyo?")
        print(result["response"])  # AI answer
        print(result["latency_ms"])  # Response time
    """
    
    CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
    DEFAULT_MODEL = "llama-4-scout-17b-16e-instruct"  # Fast model for hackathon
    
    def __init__(self, api_key: str, cerebras_api_key: str):
        super().__init__(api_key)
        self.cerebras_api_key = cerebras_api_key
        self._client: Optional[httpx.Client] = None
    
    def initialize(self) -> bool:
        """Initialize Cerebras connection."""
        if self.cerebras_api_key:
            self._client = httpx.Client(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.cerebras_api_key}",
                    "Content-Type": "application/json",
                },
            )
            self._initialized = True
            print("[SmartInference] Initialized with Cerebras API")
        else:
            self._initialized = True
            print("[SmartInference] Initialized (mock mode - no API key)")
        
        return True
    
    def query(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: str = None,
    ) -> Dict[str, Any]:
        """
        Run inference via Cerebras.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system instructions
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            model: Model to use (defaults to DEFAULT_MODEL)
            
        Returns:
            Dictionary with "response" and "latency_ms"
        """
        start_time = time.time()
        
        if self._client and self.cerebras_api_key:
            try:
                # Build messages
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Make request to Cerebras
                response = self._client.post(
                    self.CEREBRAS_URL,
                    json={
                        "model": model or self.DEFAULT_MODEL,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                response.raise_for_status()
                
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "response": answer,
                    "latency_ms": latency_ms,
                    "model": model or self.DEFAULT_MODEL,
                    "tokens_used": data.get("usage", {}),
                }
                
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "response": f"Error calling Cerebras API: {str(e)}",
                    "latency_ms": latency_ms,
                    "error": True,
                }
        
        else:
            # Mock response for testing without API key
            latency_ms = int((time.time() - start_time) * 1000) + 50  # Simulate some latency
            
            return {
                "response": f"[Mock Response] I received your query about: {prompt[:100]}... "
                           f"In a real deployment, this would be answered by Cerebras AI.",
                "latency_ms": latency_ms,
                "mock": True,
            }
    
    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()


class RaindropClient:
    """
    Unified client for all Raindrop Smart Components.
    
    Provides a single interface to:
    - SmartBuckets (document storage & RAG)
    - SmartSQL (structured queries)
    - SmartMemory (context persistence)
    - SmartInference (Cerebras LLM)
    
    Usage:
        client = RaindropClient(
            api_key="your_raindrop_key",
            cerebras_api_key="your_cerebras_key"
        )
        client.initialize_all()
        
        # Use components
        client.buckets.store("my-bucket", data)
        client.sql.insert("my-table", row)
        client.memory.store("key", value)
        result = client.inference.query("Hello!")
        
        # Cleanup
        client.close()
    """
    
    def __init__(
        self,
        api_key: str = None,
        cerebras_api_key: str = None,
    ):
        """
        Initialize the Raindrop client.
        
        Args:
            api_key: Raindrop API key (defaults to settings)
            cerebras_api_key: Cerebras API key (defaults to settings)
        """
        self.api_key = api_key or settings.raindrop_api_key
        self.cerebras_api_key = cerebras_api_key or settings.cerebras_api_key
        
        # Initialize managers
        self.buckets = BucketsManager(self.api_key)
        self.sql = SQLManager(self.api_key)
        self.memory = MemoryManager(self.api_key)
        self.inference = InferenceManager(self.api_key, self.cerebras_api_key)
        
        self._initialized = False
    
    def initialize_all(self) -> bool:
        """
        Initialize all Smart Components.
        
        Returns:
            True if all components initialized successfully
        """
        results = [
            self.buckets.initialize(),
            self.sql.initialize(),
            self.memory.initialize(),
            self.inference.initialize(),
        ]
        
        self._initialized = all(results)
        
        if self._initialized:
            print("[RaindropClient] All components initialized successfully")
        else:
            print("[RaindropClient] Some components failed to initialize")
        
        return self._initialized
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    def close(self):
        """Close all connections."""
        self.inference.close()
        print("[RaindropClient] Closed all connections")
    
    def __enter__(self):
        self.initialize_all()
        return self
    
    def __exit__(self, *args):
        self.close()

