/**
 * Clinical Data Cache Service
 * Provides caching for EHR clinical data to avoid duplicate API calls
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

export class ClinicalDataCache {
  private cache = new Map<string, CacheEntry<any>>();
  private defaultTTL = 5 * 60 * 1000; // 5 minutes

  /**
   * Get cached data
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }
    
    // Check if expired
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    
    console.log(`Cache HIT for key: ${key}`);
    return entry.data as T;
  }

  /**
   * Set cached data with optional TTL
   */
  set<T>(key: string, data: T, ttlMs?: number): void {
    const ttl = ttlMs || this.defaultTTL;
    const now = Date.now();
    
    const entry: CacheEntry<T> = {
      data,
      timestamp: now,
      expiresAt: now + ttl
    };
    
    this.cache.set(key, entry);
    console.log(`Cache SET for key: ${key}, expires in ${ttl/1000}s`);
  }

  /**
   * Clear specific cache entry
   */
  delete(key: string): void {
    this.cache.delete(key);
    console.log(`Cache DELETED for key: ${key}`);
  }

  /**
   * Clear all cache
   */
  clear(): void {
    this.cache.clear();
    console.log('Cache CLEARED all entries');
  }

  /**
   * Get cache statistics
   */
  getStats() {
    const now = Date.now();
    let expired = 0;
    let active = 0;
    
    this.cache.forEach((entry) => {
      if (now > entry.expiresAt) {
        expired++;
      } else {
        active++;
      }
    });
    
    return {
      total: this.cache.size,
      active,
      expired
    };
  }

  /**
   * Clean up expired entries
   */
  cleanup(): void {
    const now = Date.now();
    let removed = 0;
    
    const keysToDelete: string[] = [];
    this.cache.forEach((entry, key) => {
      if (now > entry.expiresAt) {
        keysToDelete.push(key);
      }
    });
    
    keysToDelete.forEach(key => {
      this.cache.delete(key);
      removed++;
    });
    
    if (removed > 0) {
      console.log(`Cache CLEANUP: removed ${removed} expired entries`);
    }
  }

  /**
   * Generate cache key for patient clinical data
   */
  static patientKey(ehrId: string, dataType: string): string {
    return `patient:${ehrId}:${dataType}`;
  }

  /**
   * Generate cache key for patient encounters
   */
  static encountersKey(ehrId: string): string {
    return `encounters:${ehrId}`;
  }
}


// Singleton instance
export const clinicalDataCache = new ClinicalDataCache();

// Auto cleanup every 2 minutes
setInterval(() => {
  clinicalDataCache.cleanup();
}, 2 * 60 * 1000);

export default clinicalDataCache;