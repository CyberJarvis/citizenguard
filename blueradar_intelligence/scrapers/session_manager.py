"""
BlueRadar - Advanced Session Manager
Cookie rotation with encryption, health monitoring, and auto-recovery
"""

import json
import time
import random
import hashlib
import base64
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading

from utils.logging_config import setup_logging

logger = setup_logging("session_manager")


class AccountStatus(Enum):
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    UNHEALTHY = "unhealthy"
    RATE_LIMITED = "rate_limited"
    BANNED = "banned"
    DISABLED = "disabled"


class RotationStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    HEALTH_BASED = "health_based"
    RANDOM = "random"
    LEAST_USED = "least_used"


@dataclass
class SessionAccount:
    """Represents a single session account with full tracking"""
    id: str
    platform: str
    session_id: str
    status: str = AccountStatus.ACTIVE.value
    request_count: int = 0
    total_requests: int = 0
    max_requests: int = 50
    health_score: int = 100
    success_rate: float = 1.0
    last_used: Optional[str] = None
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    cooldown_until: Optional[str] = None
    rate_limit_until: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)
    
    # Statistics
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SessionAccount':
        # Handle nested status conversion
        if 'status' in data and isinstance(data['status'], str):
            pass  # Keep as string
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def update_success_rate(self):
        """Update success rate based on history"""
        total = self.successful_requests + self.failed_requests
        if total > 0:
            self.success_rate = self.successful_requests / total


class CookieEncryption:
    """Simple encryption for cookie storage"""
    
    def __init__(self, key: Optional[str] = None):
        self.key = key or self._get_or_create_key()
    
    def _get_or_create_key(self) -> str:
        """Get encryption key from environment or create one"""
        env_key = os.environ.get("BLUERADAR_COOKIE_KEY")
        if env_key:
            return env_key
        
        # Generate a machine-specific key
        machine_id = hashlib.sha256(
            (os.environ.get("USER", "") + str(os.getpid())).encode()
        ).hexdigest()[:32]
        
        return machine_id
    
    def encrypt(self, data: str) -> str:
        """Simple XOR encryption (use proper encryption in production)"""
        key_bytes = self.key.encode()
        data_bytes = data.encode()
        
        encrypted = bytes([
            data_bytes[i] ^ key_bytes[i % len(key_bytes)]
            for i in range(len(data_bytes))
        ])
        
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            key_bytes = self.key.encode()
            
            decrypted = bytes([
                encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)]
                for i in range(len(encrypted_bytes))
            ])
            
            return decrypted.decode()
        except Exception:
            return encrypted_data  # Return as-is if decryption fails


class SessionManager:
    """
    Advanced session manager with:
    - Multiple rotation strategies
    - Health-based selection
    - Automatic cooldown management
    - Cookie encryption
    - Thread safety
    - Statistics tracking
    """
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        encryption_enabled: bool = True,
        rotation_strategy: RotationStrategy = RotationStrategy.HEALTH_BASED
    ):
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "cookies.json"
        self.encryption = CookieEncryption() if encryption_enabled else None
        self.rotation_strategy = rotation_strategy
        
        self.accounts: Dict[str, List[SessionAccount]] = {
            "instagram": [],
            "facebook": [],
            "twitter": []
        }
        
        self._lock = threading.Lock()
        self._current_index: Dict[str, int] = {}
        
        self._load_accounts()
        
        # Statistics
        self.stats = {
            "total_rotations": 0,
            "total_cooldowns": 0,
            "total_recoveries": 0
        }
        
        logger.info(f"Session Manager initialized with {self.rotation_strategy.value} strategy")
    
    def _load_accounts(self):
        """Load accounts from config file"""
        if not self.config_path.exists():
            logger.info("No existing cookie config found, starting fresh")
            return
            
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            for platform, accounts in data.get("accounts", {}).items():
                if platform not in self.accounts:
                    self.accounts[platform] = []
                    
                for acc_data in accounts:
                    # Decrypt session ID if encrypted
                    if self.encryption and acc_data.get("encrypted"):
                        acc_data["session_id"] = self.encryption.decrypt(
                            acc_data["session_id"]
                        )
                    
                    account = SessionAccount.from_dict(acc_data)
                    self.accounts[platform].append(account)
            
            total = sum(len(v) for v in self.accounts.values())
            logger.info(f"Loaded {total} accounts from config")
            
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
    
    def _save_accounts(self):
        """Save accounts to config file with encryption"""
        try:
            data = {"accounts": {}, "updated_at": datetime.now().isoformat()}
            
            for platform, accounts in self.accounts.items():
                data["accounts"][platform] = []
                
                for acc in accounts:
                    acc_dict = acc.to_dict()
                    
                    # Encrypt session ID
                    if self.encryption:
                        acc_dict["session_id"] = self.encryption.encrypt(acc.session_id)
                        acc_dict["encrypted"] = True
                    
                    data["accounts"][platform].append(acc_dict)
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving accounts: {e}")
    
    def add_account(
        self,
        platform: str,
        session_id: str,
        account_id: Optional[str] = None,
        max_requests: int = 50,
        metadata: Optional[Dict] = None
    ) -> SessionAccount:
        """Add a new session account"""
        with self._lock:
            if platform not in self.accounts:
                self.accounts[platform] = []
            
            acc_id = account_id or f"{platform}_{len(self.accounts[platform]) + 1}"
            
            account = SessionAccount(
                id=acc_id,
                platform=platform,
                session_id=session_id,
                max_requests=max_requests,
                metadata=metadata or {}
            )
            
            self.accounts[platform].append(account)
            self._save_accounts()
            
            logger.info(f"Added account {acc_id} for {platform}")
            return account
    
    def remove_account(self, platform: str, account_id: str) -> bool:
        """Remove an account"""
        with self._lock:
            accounts = self.accounts.get(platform, [])
            for i, acc in enumerate(accounts):
                if acc.id == account_id:
                    del accounts[i]
                    self._save_accounts()
                    logger.info(f"Removed account {account_id}")
                    return True
            return False
    
    def get_active_session(self, platform: str) -> Optional[SessionAccount]:
        """Get the best available session based on rotation strategy"""
        with self._lock:
            self._update_statuses(platform)
            
            active_accounts = [
                acc for acc in self.accounts.get(platform, [])
                if acc.status == AccountStatus.ACTIVE.value
                and acc.health_score >= 20
            ]
            
            if not active_accounts:
                logger.warning(f"No active sessions for {platform}")
                return None
            
            # Select based on strategy
            selected = self._select_by_strategy(active_accounts, platform)
            
            if selected:
                logger.debug(
                    f"Selected {selected.id} "
                    f"(health: {selected.health_score}, requests: {selected.request_count})"
                )
            
            return selected
    
    def _select_by_strategy(
        self,
        accounts: List[SessionAccount],
        platform: str
    ) -> Optional[SessionAccount]:
        """Select account based on rotation strategy"""
        
        if not accounts:
            return None
        
        if self.rotation_strategy == RotationStrategy.ROUND_ROBIN:
            # Simple round-robin
            idx = self._current_index.get(platform, 0)
            selected = accounts[idx % len(accounts)]
            self._current_index[platform] = (idx + 1) % len(accounts)
            return selected
        
        elif self.rotation_strategy == RotationStrategy.HEALTH_BASED:
            # Sort by health score (desc), then by requests (asc)
            accounts.sort(key=lambda x: (-x.health_score, x.request_count))
            return accounts[0]
        
        elif self.rotation_strategy == RotationStrategy.RANDOM:
            # Random selection
            return random.choice(accounts)
        
        elif self.rotation_strategy == RotationStrategy.LEAST_USED:
            # Select least used account
            accounts.sort(key=lambda x: x.total_requests)
            return accounts[0]
        
        return accounts[0]
    
    def _update_statuses(self, platform: str):
        """Update cooldown and rate limit statuses"""
        now = datetime.now()
        
        for acc in self.accounts.get(platform, []):
            # Check cooldown expiry
            if acc.status == AccountStatus.COOLDOWN.value and acc.cooldown_until:
                try:
                    cooldown_end = datetime.fromisoformat(acc.cooldown_until)
                    if now >= cooldown_end:
                        acc.status = AccountStatus.ACTIVE.value
                        acc.cooldown_until = None
                        acc.request_count = 0
                        acc.health_score = min(100, acc.health_score + 30)
                        self.stats["total_recoveries"] += 1
                        logger.info(f"Account {acc.id} recovered from cooldown")
                except Exception:
                    pass
            
            # Check rate limit expiry
            if acc.status == AccountStatus.RATE_LIMITED.value and acc.rate_limit_until:
                try:
                    rate_limit_end = datetime.fromisoformat(acc.rate_limit_until)
                    if now >= rate_limit_end:
                        acc.status = AccountStatus.ACTIVE.value
                        acc.rate_limit_until = None
                        acc.health_score = min(100, acc.health_score + 10)
                        logger.info(f"Account {acc.id} rate limit expired")
                except Exception:
                    pass
    
    def record_request(
        self,
        platform: str,
        account_id: str,
        success: bool = True,
        rate_limited: bool = False
    ):
        """Record a request and update account status"""
        with self._lock:
            account = self._get_account(platform, account_id)
            if not account:
                return
            
            account.request_count += 1
            account.total_requests += 1
            account.last_used = datetime.now().isoformat()
            
            if rate_limited:
                self._handle_rate_limit(account)
            elif success:
                self._handle_success(account)
            else:
                self._handle_failure(account)
            
            # Check if max requests reached
            if account.request_count >= account.max_requests:
                self._put_on_cooldown(account, "max_requests_reached")
            
            account.update_success_rate()
            self._save_accounts()
    
    def _handle_success(self, account: SessionAccount):
        """Handle successful request"""
        account.successful_requests += 1
        account.last_success = datetime.now().isoformat()
        
        # Slight health recovery
        account.health_score = min(100, account.health_score + 2)
    
    def _handle_failure(self, account: SessionAccount):
        """Handle failed request"""
        account.failed_requests += 1
        account.last_failure = datetime.now().isoformat()
        
        # Health decrease
        account.health_score = max(0, account.health_score - 15)
        
        if account.health_score < 20:
            account.status = AccountStatus.UNHEALTHY.value
            logger.warning(f"Account {account.id} marked unhealthy (health: {account.health_score})")
    
    def _handle_rate_limit(self, account: SessionAccount):
        """Handle rate limit hit"""
        account.rate_limit_hits += 1
        account.status = AccountStatus.RATE_LIMITED.value
        account.rate_limit_until = (
            datetime.now() + timedelta(minutes=15)
        ).isoformat()
        account.health_score = max(0, account.health_score - 30)
        
        logger.warning(f"Account {account.id} rate limited, cooling down for 15 minutes")
    
    def _put_on_cooldown(self, account: SessionAccount, reason: str = ""):
        """Put account on cooldown"""
        account.status = AccountStatus.COOLDOWN.value
        account.cooldown_until = (
            datetime.now() + timedelta(minutes=30)
        ).isoformat()
        account.request_count = 0
        
        self.stats["total_cooldowns"] += 1
        logger.info(f"Account {account.id} on cooldown: {reason}")
    
    def _get_account(self, platform: str, account_id: str) -> Optional[SessionAccount]:
        """Get account by ID"""
        for acc in self.accounts.get(platform, []):
            if acc.id == account_id:
                return acc
        return None
    
    def get_session_cookie(self, platform: str) -> Optional[Dict]:
        """Get session cookie for platform"""
        account = self.get_active_session(platform)
        if not account:
            return None
        
        # Platform-specific cookie configuration
        cookie_configs = {
            "instagram": {
                "name": "sessionid",
                "domain": ".instagram.com",
                "path": "/"
            },
            "facebook": {
                "name": "c_user",  # Facebook uses different cookie
                "domain": ".facebook.com",
                "path": "/"
            },
            "twitter": {
                "name": "auth_token",
                "domain": ".twitter.com",
                "path": "/"
            }
        }
        
        config = cookie_configs.get(platform, {
            "name": "sessionid",
            "domain": f".{platform}.com",
            "path": "/"
        })
        
        return {
            "account_id": account.id,
            "session_id": account.session_id,
            "cookie": {
                **config,
                "value": account.session_id
            }
        }
    
    def rotate_session(
        self,
        platform: str,
        current_account_id: str,
        reason: str = "manual"
    ) -> Optional[SessionAccount]:
        """Force rotate to next available session"""
        with self._lock:
            current = self._get_account(platform, current_account_id)
            if current:
                self._put_on_cooldown(current, f"forced_rotation: {reason}")
            
            self.stats["total_rotations"] += 1
            return self.get_active_session(platform)
    
    def setup_instagram_cookies(self, session_ids: List[str], max_requests: int = 50):
        """Quick setup for multiple Instagram cookies"""
        for i, sid in enumerate(session_ids, 1):
            sid = sid.strip()
            if sid:
                self.add_account(
                    platform="instagram",
                    session_id=sid,
                    account_id=f"instagram_{i}",
                    max_requests=max_requests
                )
        
        logger.info(f"Setup {len(session_ids)} Instagram accounts")
    
    def setup_facebook_cookies(self, session_ids: List[str], max_requests: int = 30):
        """Quick setup for Facebook cookies"""
        for i, sid in enumerate(session_ids, 1):
            sid = sid.strip()
            if sid:
                self.add_account(
                    platform="facebook",
                    session_id=sid,
                    account_id=f"facebook_{i}",
                    max_requests=max_requests
                )
    
    def get_status(self) -> Dict:
        """Get detailed status of all accounts"""
        status = {"platforms": {}, "statistics": self.stats}
        
        for platform, accounts in self.accounts.items():
            platform_status = {
                "total": len(accounts),
                "active": sum(1 for a in accounts if a.status == AccountStatus.ACTIVE.value),
                "cooldown": sum(1 for a in accounts if a.status == AccountStatus.COOLDOWN.value),
                "rate_limited": sum(1 for a in accounts if a.status == AccountStatus.RATE_LIMITED.value),
                "unhealthy": sum(1 for a in accounts if a.status == AccountStatus.UNHEALTHY.value),
                "accounts": []
            }
            
            for acc in accounts:
                platform_status["accounts"].append({
                    "id": acc.id,
                    "status": acc.status,
                    "health": acc.health_score,
                    "requests": acc.request_count,
                    "total_requests": acc.total_requests,
                    "success_rate": f"{acc.success_rate:.1%}",
                    "cooldown_until": acc.cooldown_until
                })
            
            status["platforms"][platform] = platform_status
        
        return status
    
    def validate_cookies(self, platform: str) -> Dict[str, bool]:
        """Validate all cookies for a platform (basic check)"""
        results = {}
        
        for acc in self.accounts.get(platform, []):
            # Basic validation - check if session ID looks valid
            is_valid = (
                acc.session_id and
                len(acc.session_id) > 10 and
                acc.health_score > 0
            )
            results[acc.id] = is_valid
        
        return results
    
    def export_config(self, filepath: Path):
        """Export configuration to file"""
        status = self.get_status()
        with open(filepath, 'w') as f:
            json.dump(status, f, indent=2)
        logger.info(f"Exported config to {filepath}")
    
    def reset_all_accounts(self, platform: Optional[str] = None):
        """Reset all accounts to active state"""
        platforms = [platform] if platform else list(self.accounts.keys())
        
        for plat in platforms:
            for acc in self.accounts.get(plat, []):
                acc.status = AccountStatus.ACTIVE.value
                acc.request_count = 0
                acc.health_score = 100
                acc.cooldown_until = None
                acc.rate_limit_until = None
        
        self._save_accounts()
        logger.info(f"Reset all accounts for: {platforms}")


# Global session manager instance
session_manager = SessionManager()
