"""
New Lighter client implementation that uses lighter_wss_maker for WebSocket and market making functionality.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable

from lighter_wss_maker import LighterWSSMaker, OrderResult, OrderInfo
from lighter_price_manager import PriceData


class LighterNew:
    """
    New Lighter client that leverages the WebSocket and market making capabilities
    from LighterWSSMaker while providing a simplified interface for trading operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the new Lighter client."""
        self.config = config
        
        # Initialize the WSS Maker client for core functionality
        self.wss_maker = LighterWSSMaker(config)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Trading state
        self._is_connected = False
        self._position_callbacks = []
        self._price_callbacks = []

    async def connect(self) -> None:
        """Connect to Lighter exchange."""
        try:
            await self.wss_maker.connect()
            self._is_connected = True
            
            # Set up price update callbacks
            self.wss_maker.add_price_update_callback(self._handle_price_update)
            
            self.logger.info("LighterNew connected successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to connect LighterNew: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Lighter exchange."""
        try:
            # Remove callbacks
            self.wss_maker.remove_price_update_callback(self._handle_price_update)
            
            await self.wss_maker.disconnect()
            self._is_connected = False
            self.logger.info("LighterNew disconnected successfully")
            
        except Exception as e:
            self.logger.error(f"Error during LighterNew disconnect: {e}")

    def _handle_price_update(self, price_data: PriceData) -> None:
        """Handle price updates from the price manager."""
        # Notify price callbacks
        for callback in self._price_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(price_data))
                else:
                    callback(price_data)
            except Exception as e:
                self.logger.error(f"Error in price callback: {e}")

    # Simplified Trading Interface
    async def place_market_order(self, symbol: str, quantity: Decimal, side: str) -> OrderResult:
        """
        Place a market order (implementation using limit orders near current price).
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: 'buy' or 'sell'
            
        Returns:
            OrderResult with order details
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to exchange")

        # Get current market price
        price_manager = self.wss_maker.get_price_manager()
        best_bid, best_ask = await price_manager.get_bbo_prices()
        
        # Calculate aggressive price for market order simulation
        if side.lower() == 'buy':
            # For buy market order, use slightly above best ask
            price = best_ask * Decimal('1.001')  # 0.1% above ask
        else:
            # For sell market order, use slightly below best bid
            price = best_bid * Decimal('0.999')  # 0.1% below bid

        self.logger.info(f"Placing market {side} order for {quantity} {symbol} at {price}")
        
        return await self.wss_maker.place_limit_order(symbol, quantity, price, side)

    async def place_limit_order(self, symbol: str, quantity: Decimal, 
                               price: Decimal, side: str) -> OrderResult:
        """
        Place a limit order.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price
            side: 'buy' or 'sell'
            
        Returns:
            OrderResult with order details
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to exchange")

        self.logger.info(f"Placing limit {side} order for {quantity} {symbol} at {price}")
        return await self.wss_maker.place_limit_order(symbol, quantity, price, side)

    async def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel an order."""
        if not self._is_connected:
            raise ConnectionError("Not connected to exchange")

        self.logger.info(f"Cancelling order {order_id}")
        return await self.wss_maker.cancel_order(order_id)

    async def cancel_all_orders(self, symbol: str) -> List[OrderResult]:
        """Cancel all orders for a symbol."""
        if not self._is_connected:
            raise ConnectionError("Not connected to exchange")

        active_orders = await self.wss_maker.get_active_orders(symbol)
        results = []
        
        for order in active_orders:
            result = await self.wss_maker.cancel_order(order.order_id)
            results.append(result)
            
        self.logger.info(f"Cancelled {len(results)} orders for {symbol}")
        return results

    # Price and Market Data
    async def get_current_price(self, symbol: str) -> Optional[PriceData]:
        """Get current price data for a symbol."""
        return await self.wss_maker.get_price_manager().get_current_price()

    async def get_bbo_prices(self, symbol: str) -> tuple[Decimal, Decimal]:
        """Get best bid/offer prices for a symbol."""
        return await self.wss_maker.get_price_manager().get_bbo_prices()

    async def get_mid_price(self, symbol: str) -> Decimal:
        """Get mid price for a symbol."""
        return await self.wss_maker.get_price_manager().get_mid_price()

    async def get_spread(self, symbol: str) -> Decimal:
        """Get spread for a symbol."""
        return await self.wss_maker.get_price_manager().get_spread()

    # Account Information
    async def get_account_balance(self) -> Dict[str, Decimal]:
        """Get account balances."""
        # This would need to be implemented based on Lighter's API
        # For now, return a placeholder
        return {"USDC": Decimal('1000.0')}  # Example balance

    async def get_position(self, symbol: str) -> Decimal:
        """Get current position for a symbol."""
        return await self.wss_maker.get_account_positions()

    async def get_active_orders(self, symbol: str) -> List[OrderInfo]:
        """Get active orders for a symbol."""
        return await self.wss_maker.get_active_orders(symbol)

    # Callback Management
    def add_price_callback(self, callback: Callable) -> None:
        """Add callback for price updates."""
        if callback not in self._price_callbacks:
            self._price_callbacks.append(callback)

    def remove_price_callback(self, callback: Callable) -> None:
        """Remove price callback."""
        if callback in self._price_callbacks:
            self._price_callbacks.remove(callback)

    def add_position_callback(self, callback: Callable) -> None:
        """Add callback for position updates."""
        if callback not in self._position_callbacks:
            self._position_callbacks.append(callback)

    def remove_position_callback(self, callback: Callable) -> None:
        """Remove position callback."""
        if callback in self._position_callbacks:
            self._position_callbacks.remove(callback)

    # Utility Methods
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the connection."""
        status = {
            'connected': self._is_connected,
            'price_manager_status': self.wss_maker.get_price_manager().get_connection_status(),
            'has_active_orders': len(await self.get_active_orders(self.config.ticker)) > 0
        }
        
        try:
            # Test price data availability
            price_data = await self.get_current_price(self.config.ticker)
            status['price_data_available'] = price_data is not None and price_data.is_valid()
        except:
            status['price_data_available'] = False
            
        return status


# Example usage and trading strategy
class SimpleMarketMaker:
    """Simple market making strategy using LighterNew."""
    
    def __init__(self, lighter_client: LighterNew, symbol: str):
        self.client = lighter_client
        self.symbol = symbol
        self.is_running = False
        
    async def start(self):
        """Start the market making strategy."""
        await self.client.connect()
        
        # Add price callbacks
        self.client.add_price_callback(self.on_price_update)
        
        self.is_running = True
        print(f"Market maker started for {self.symbol}")
        
    async def stop(self):
        """Stop the market making strategy."""
        # Cancel all orders
        await self.client.cancel_all_orders(self.symbol)
        
        # Remove callbacks
        self.client.remove_price_callback(self.on_price_update)
        
        await self.client.disconnect()
        self.is_running = False
        print("Market maker stopped")
        
    async def on_price_update(self, price_data: PriceData):
        """Handle price updates and adjust orders."""
        if not self.is_running:
            return
            
        print(f"Price update: {price_data.best_bid} - {price_data.best_ask} "
              f"(Spread: {price_data.spread})")
        
        # Simple market making logic
        # Place bid at mid price - spread/4
        # Place ask at mid price + spread/4
        bid_price = price_data.mid_price - price_data.spread / Decimal('4')
        ask_price = price_data.mid_price + price_data.spread / Decimal('4')
        
        quantity = Decimal('0.1')  # Example quantity
        
        try:
            # Cancel existing orders first
            await self.client.cancel_all_orders(self.symbol)
            
            # Place new orders
            await self.client.place_limit_order(self.symbol, quantity, bid_price, 'buy')
            await self.client.place_limit_order(self.symbol, quantity, ask_price, 'sell')
            
            print(f"Placed orders: Buy@{bid_price}, Sell@{ask_price}")
            
        except Exception as e:
            print(f"Error placing orders: {e}")


async def main():
    """Example usage of LighterNew."""
    config = {
        'ticker': 'ETH-USDC',
        'contract_id': '1',  # This will be set by get_contract_attributes
        'close_order_side': 'sell',
        'tick_size': Decimal('0.01')
    }
    
    # Initialize client
    client = LighterNew(config)
    
    try:
        # Connect to exchange
        await client.connect()
        
        # Perform health check
        health = await client.health_check()
        print(f"Health check: {health}")
        
        # Get current prices
        bid, ask = await client.get_bbo_prices(config['ticker'])
        print(f"Current prices: Bid={bid}, Ask={ask}")
        
        # Example: Place a limit order
        # order_result = await client.place_limit_order(
        #     config['ticker'], 
        #     Decimal('0.1'), 
        #     (bid + ask) / 2, 
        #     'buy'
        # )
        # print(f"Order result: {order_result}")
        
        # Get active orders
        active_orders = await client.get_active_orders(config['ticker'])
        print(f"Active orders: {len(active_orders)}")
        
        # Get position
        position = await client.get_position(config['ticker'])
        print(f"Current position: {position}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())