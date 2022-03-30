from scipy.optimize import minimize


def optimize(dist, init_vals, lower, upper, mass):
    def prob_bound(params, dist, lower, upper, mass):
        dist._update(*params)  # pylint: disable=protected-access
        rv_frozen = dist.rv_frozen
        cdf0 = rv_frozen.cdf(lower)
        cdf1 = rv_frozen.cdf(upper)
        loss = (cdf1 - cdf0) - mass
        return loss

    cons = {
        "type": "eq",
        "fun": prob_bound,
        "args": (dist, lower, upper, mass),
    }

    opt = minimize(
        dist._entropy_loss, x0=init_vals, constraints=cons  # pylint: disable=protected-access
    )
    return opt


def relative_error(rv_frozen, upper, lower, requiered_mass):
    computed_mass = rv_frozen.cdf(upper) - rv_frozen.cdf(lower)
    return (computed_mass - requiered_mass) / requiered_mass * 100
