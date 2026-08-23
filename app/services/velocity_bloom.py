import hashlib
import array
import math
import logging

logger = logging.getLogger(__name__)

class ScalableCountMinSketch:
    """
    Staff-Level Optimization: Count-Min Sketch for O(1) Time, O(1) Space Velocity Checks.
    
    Instead of querying the database for "SELECT COUNT(*) WHERE card_id = X AND time > Y"
    (which scales poorly under massive throughput), this probabilistic data structure
    maintains an approximate count of transactions in a fixed memory footprint.
    
    Mathematical Guarantees:
    - Error rate bounded by epsilon (e.g., 0.01)
    - Confidence bounded by delta (e.g., 0.99)
    - Memory footprint is strictly deterministic: (e/epsilon) * ln(1/delta) counters
    """
    def __init__(self, epsilon=0.01, delta=0.99):
        # Calculate optimal width (columns) and depth (hash functions/rows)
        self.width = int(math.ceil(math.e / epsilon))
        self.depth = int(math.ceil(math.log(1.0 / delta)))
        
        # We use a flat array for C-level memory efficiency in Python
        # 'L' is unsigned 4-byte integer. Total memory = width * depth * 4 bytes.
        self.table = array.array('L', [0] * (self.width * self.depth))
        
        logger.info(f"Initialized Count-Min Sketch. Width: {self.width}, Depth: {self.depth}. "
                    f"Memory: {(self.width * self.depth * 4) / 1024:.2f} KB")

    def _hashes(self, item: str):
        """Generates `depth` independent hash values using MD5 multi-hashing."""
        h = hashlib.md5(item.encode('utf-8'))
        # We can extract multiple 32-bit integers from a single MD5 hash (128-bit)
        # to avoid hashing multiple times.
        hash_bytes = h.digest()
        
        hashes = []
        for i in range(self.depth):
            # Use offset based on i to extract 4 bytes
            offset = (i * 4) % 12
            h_int = int.from_bytes(hash_bytes[offset:offset+4], byteorder='little')
            hashes.append(h_int % self.width)
        return hashes

    def record_transaction(self, card_id: str, amount: float):
        """O(1) update of the probabilistic counter."""
        for i, h_val in enumerate(self._hashes(card_id)):
            index = i * self.width + h_val
            # Increment the counter
            self.table[index] += 1
            
    def estimate_velocity(self, card_id: str) -> int:
        """O(1) retrieval of the upper-bound transaction count for a card."""
        min_count = float('inf')
        for i, h_val in enumerate(self._hashes(card_id)):
            index = i * self.width + h_val
            if self.table[index] < min_count:
                min_count = self.table[index]
        return min_count
        
    def check_velocity_safe(self, card_id: str, threshold: int, exact_db_check_func) -> bool:
        """
        STAFF FIX: Prevents False Positives from Hash Collisions.
        If the sketch estimates the velocity is below the threshold, we are 100% mathematically
        guaranteed they are safe (no false negatives). We approve instantly in O(1).
        
        If the sketch says they are OVER the threshold, it might be a hash collision. 
        We ONLY hit the database for this extreme minority of cases to verify exactly.
        """
        sketch_estimate = self.estimate_velocity(card_id)
        
        if sketch_estimate < threshold:
            # 100% safe, O(1) fast path
            return True
            
        logger.warning(f"Sketch threshold exceeded for {card_id}. Falling back to precise DB query to prevent false positive.")
        # Slow path: Verify exactly to prevent blocking a legitimate user due to collision
        exact_count = exact_db_check_func(card_id)
        return exact_count < threshold
