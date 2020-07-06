import math


class StableStrategy(object):
    """
    StableStrategy() class

    Class that creates order parameters to be ready for execution. This class do not
    place the orders.

    __init__ Parameters
    -----------
    weights_params: Dictionary with parameters for weight distribution.
        type str: Type of weights for orders. Possible values: lin, exp, log. Default is lin.
        exp_constant int: Constant that adjusts the rate of the exponential/log weights.  Default is 1.
        descending bool: Sets the order of the weights of the orders. Descending False implies bigger weights are in extreme prices.

    price_deviation_params: Dictionary with parameters for price deviation distribution.
        step float: The step for which the prices of the orders will vary. This will be above and below the stable price.
        type str: Type of price deviation for orders. Possible values: lin, exp, log.  Default is lin.
        exp_constant_1 int: Constant that measures the amplitude of the exponential/log deviations. It's the A in A * e ** (C * x). Default is 0.001.
        exp_constant_2 int: Constant that measures the rate of the exponential/log deviations. It's the C in A * e ** (C * x). Default is 1.

    decimal_round: number of decimals to round price and amounts. Default is 5


    methods:
    -----------
    get_order_weights: set up the weights of the orders depending on the type already defined.
    get_price_deviations: set up the deviations of the orders from the stable price depending on the step and type already defined.
    build_orders: Build orders to sell or to buy.
    check_orders_with_fee: check that created orders comply with the fee of the exchange.
    get_orders: get sell & buy orders ready to be placed in exchange.


    """

    def __init__(
        self,
        weights_params={"type": "lin", "descending": True, "exp_constant": 1},
        price_deviation_params={
            "type": "lin",
            "step": 0.1,
            "exp_constant_1": 0.001,
            "exp_constant_2": 1,
            "linear_spread": 0,
        },
        decimal_round=5,
    ):

        self.weights_type = weights_params["type"]
        self.weights_constant = weights_params["exp_constant"]
        self.weights_desc = weights_params["descending"]
        self.price_deviation_step = price_deviation_params["step"]
        self.price_deviation_type = price_deviation_params["type"]
        self.price_deviation_constant_1 = price_deviation_params["exp_constant_1"]
        self.price_deviation_constant_2 = price_deviation_params["exp_constant_2"]
        self.decimal_round = decimal_round

        assert self.price_deviation_type in [
            "exp",
            "lin",
            "log",
        ], "Deviation type not accepted. Please use exp, lin or log"
        assert self.weights_type in [
            "exp",
            "lin",
            "log",
        ], "Weights type not accepted.  Please use exp, lin or log"

    def get_order_weights(self, n_orders):
        if self.weights_type == "lin":
            return [1 / n_orders] * n_orders
        elif self.weights_type == "exp":
            values = [
                math.exp(self.weights_constant * i) for i in range(1, n_orders + 1)
            ]
            return [x / sum(values) for x in values]
        elif self.weights_type == "log":
            values = [
                math.log(self.weights_constant * i) for i in range(2, n_orders + 2)
            ]
            return [x / sum(values) for x in values]

    def get_price_deviations(self, n_orders):
        if self.price_deviation_type == "lin":
            return [self.price_deviation_step * i for i in range(1, n_orders + 1)]
        elif self.price_deviation_type == "exp":
            values = [
                self.price_deviation_constant_1
                * math.exp(self.price_deviation_constant_2 * i)
                for i in range(1, n_orders + 1)
            ]
            values = sorted(values)
            return values
        elif self.price_deviation_type == "log":
            return [
                self.price_deviation_constant_1
                * math.log(self.price_deviation_constant_2 * i)
                for i in range(2, n_orders + 2)
            ]

    def build_orders(
        self,
        n_orders,
        reference_price,
        balance,
        min_amount,
        price_limit,
        pos_constant,
        balance_coverage,
        price_deviation_spread,
    ):

        if n_orders == 0:
            return []

        price_deviations = self.get_price_deviations(n_orders)
        order_weights = sorted(
            self.get_order_weights(n_orders), reverse=self.weights_desc
        )

        orders = []

        invalid_orders = False
        outside_price_range = False

        for p_dev, w in zip(price_deviations, order_weights):

            price = round(
                reference_price * (1 + pos_constant * p_dev)
                + pos_constant * price_deviation_spread,
                self.decimal_round,
            )

            # Orders with negative amount are to sell
            amount = round(
                -pos_constant * balance * w * balance_coverage, self.decimal_round
            )

            if abs(amount) < min_amount or price < (reference_price / 10):
                invalid_orders = True

            if (pos_constant == -1 and price > price_limit) or (
                pos_constant == 1 and price < price_limit
            ):
                outside_price_range = True

            orders.append((price, amount))

        if invalid_orders:
            n_orders -= 1
            return self.build_orders(
                n_orders,
                reference_price,
                balance,
                min_amount,
                price_limit,
                pos_constant,
                balance_coverage,
                price_deviation_spread,
            )

        elif outside_price_range:
            reference_price += pos_constant * (reference_price / 100)
            return self.build_orders(
                n_orders,
                reference_price,
                balance,
                min_amount,
                price_limit,
                pos_constant,
                balance_coverage,
                price_deviation_spread,
            )

        else:
            return orders

    def check_orders_with_fee(self, orders, fee, min_profit):
        sell_orders = sorted([x for x in orders if x[-1] < 0])
        buy_orders = sorted([x for x in orders if x[-1] > 0])

        if not len(sell_orders) or not len(buy_orders):
            return True

        min_sell_price = sell_orders[0][0]
        max_buy_price = buy_orders[-1][0]
        if (min_sell_price - max_buy_price) / max_buy_price > 2 * fee + min_profit:
            return True
        else:
            return False

    def get_orders(
        self,
        n_orders,
        reference_price,
        sell_balance,
        buy_balance,
        min_amount,
        min_sell_price,
        max_buy_price,
        fee,
        min_profit,
        price_deviation_spread=0,
        balance_coverage=0.999,
    ):

        """ get_orders

        Set up the orders to be placed in an exchange

        Parameters
        -----------
            reference_price: The middle price in which we separate the orders
            sell_balance: The amount available to sell
            buy_balance: The amount available to buy
            min_amount: Exchange limit amount for an order to be placed.
            min_sell_price: Minimum price to sell.
            max_buy_price: Maximum price to sell.
            fee: Fee of the exchange.
            min_profit: Profit minimum that is perceived.
            price_deviation_spread: Minimum spread of price deviations.
            balance_coverage: percentage of balance that will be divided in orders. Recommended to be != 1 because rounding numbers could lead to sums over the total balance.

        Returns
        -----------
            orders: List of tuples containing the information of price and amount for the order to be placed

        """

        orders = []

        for pos_constant, balance, price_lim in [
            (1, sell_balance, min_sell_price),
            (-1, buy_balance, max_buy_price),
        ]:

            orders += self.build_orders(
                n_orders,
                reference_price,
                balance,
                min_amount,
                price_lim,
                pos_constant,
                balance_coverage,
                price_deviation_spread,
            )

        if not len(orders):
            return []

        elif self.check_orders_with_fee(orders, fee, min_profit):
            return orders

        else:
            price_deviation_spread += reference_price / 100

            return self.get_orders(
                n_orders,
                reference_price,
                sell_balance,
                buy_balance,
                min_amount,
                min_sell_price,
                max_buy_price,
                fee,
                min_profit,
                price_deviation_spread,
                balance_coverage,
            )
