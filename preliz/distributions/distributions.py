"""
Parent classes for all families.
"""
# pylint: disable=no-member
from collections import namedtuple

try:
    from ipywidgets import interactive
except ImportError:
    pass
import numpy as np

from ..internal.plot_helper import (
    plot_pdfpmf,
    plot_cdf,
    plot_ppf,
    get_slider,
    check_inside_notebook,
)
from ..internal.distribution_helper import (
    init_vals,
    valid_scalar_params,
    valid_distribution,
    hdi_from_pdf,
)


class Distribution:
    """
    Base class for distributions.

    Not intended for direct instantiation.
    """

    def __init__(self):
        self.rv_frozen = None
        self.is_frozen = False
        self.opt = None

    def __repr__(self):
        name = self.__class__.__name__
        if self.is_frozen:
            bolded_name = "\033[1m" + name + "\033[0m"

            description = "".join(
                f"{n}={np.round(v, 2)}," for n, v in zip(self.param_names, self.params)
            ).strip(",")

            return f"{bolded_name}({description})"
        else:
            return name

    def _update_rv_frozen(self):
        """Update the rv_frozen object"""

        frozen = self._get_frozen()
        if frozen is not None:
            self.is_frozen = True
            self.rv_frozen = frozen

    def summary(self, mass=0.94, fmt=".2f"):
        """
        Namedtuple with the mean, median, standard deviation, and lower and upper bounds
        of the equal-tailed interval.

        Parameters
        ----------
        mass: float
            Probability mass for the equal-tailed interval. Defaults to 0.94
        fmt : str
            fmt used to represent results using f-string fmt for floats. Default to ".2f"
            i.e. 2 digits after the decimal point.
        """
        valid_distribution(self)

        if not isinstance(fmt, str):
            raise ValueError("Invalid format string.")

        if valid_scalar_params(self):
            attr = namedtuple(self.__class__.__name__, ["mean", "median", "std", "lower", "upper"])
            mean = float(f"{self.mean():{fmt}}")
            median = float(f"{self.median():{fmt}}")
            std = float(f"{self.std():{fmt}}")
            eti = self.eti(mass)
            lower_tail = float(f"{eti[0]:{fmt}}")
            upper_tail = float(f"{eti[1]:{fmt}}")
            return attr(mean, median, std, lower_tail, upper_tail)
        else:
            return None

    def rvs(self, *args, **kwds):
        """Random sample

        Parameters
        ----------
        size : int or tuple of ints, optional
            Defining number of random variates. Defaults to 1.
        random_state : {None, int, numpy.random.Generator, numpy.random.RandomState}
            Defaults to None
        """
        return self.rv_frozen.rvs(*args, **kwds)

    def cdf(self, x, *args, **kwds):
        """Cumulative distribution function.

        Parameters
        ----------
        x : array_like
            Values on which to evaluate the cdf
        """
        return self.rv_frozen.cdf(x, *args, **kwds)

    def ppf(self, q, *args, **kwds):
        """Percent point function (inverse of cdf).

        Parameters
        ----------
        x : array_like
            Values on which to evaluate the inverse of the cdf
        """
        return self.rv_frozen.ppf(q, *args, **kwds)

    def mean(self):
        """Mean of the distribution."""
        return self.rv_frozen.mean()

    def median(self):
        """Median of the distribution."""
        return self.rv_frozen.median()

    def std(self):
        """Standard deviation of the distribution."""
        return self.rv_frozen.std()

    def var(self):
        """Variance of the distribution."""
        return self.rv_frozen.var()

    def skewness(self):
        """Skewness of the distribution."""
        return self.stats(moment="s")

    def kurtois(self):
        """Kurtosis of the distribution"""
        return self.stats(moments="k")

    def moments(self, types="mvsk"):
        """
        Compute moments of the distribution.

        It can also return the standard deviation

        Parameters
        ----------
        types : str
            The type of moments to compute. Default is 'mvsk'
            where 'm' = mean, 'v' = variance, 's' = skewness, and 'k' = kurtosis.
            Valid combinations are any subset of 'mvsk'.
        """
        if self.rv_frozen is None:
            moments = []
            for m_t in types:
                if m_t not in "mdvsk":
                    raise ValueError(
                        "The input string should only contain the letters "
                        "'m', 'd', 'v', 's', or 'k'."
                    )
                if m_t == "m":
                    moments.append(self.mean())
                elif m_t == "d":
                    moments.append(self.std())
                elif m_t == "v":
                    moments.append(self.var())
                elif m_t == "s":
                    moments.append(self.skewness())
                elif m_t == "k":
                    moments.append(self.kurtosis())
        else:
            moments = self.rv_frozen.stats(moments=types)

        return moments

    def eti(self, mass=0.94, fmt=".2f"):
        """Equal-tailed interval containing `mass`.

        Parameters
        ----------
        mass: float
            Probability mass in the interval. Defaults to 0.94
        fmt : str
            fmt used to represent results using f-string fmt for floats. Default to ".2f"
            i.e. 2 digits after the decimal point.
        """
        valid_distribution(self)

        if not isinstance(fmt, str):
            raise ValueError("Invalid format string.")

        if valid_scalar_params(self):
            if self.rv_frozen is None:
                eti_b = self.ppf([(1 - mass) / 2, 1 - (1 - mass) / 2])
            else:
                eti_b = self.rv_frozen.interval(mass)
            lower_tail = float(f"{eti_b[0]:{fmt}}")
            upper_tail = float(f"{eti_b[1]:{fmt}}")
            return (lower_tail, upper_tail)
        else:
            return None

    def hdi(self, mass=0.94, fmt=".2f"):
        """Highest density interval containing `mass`.

        Parameters
        ----------
        mass: float
            Probability mass in the interval. Defaults to 0.94
        fmt : str
            fmt used to represent results using f-string fmt for floats. Default to ".2f"
            i.e. 2 digits after the decimal point.
        """
        valid_distribution(self)

        if not isinstance(fmt, str):
            raise ValueError("Invalid format string.")

        if valid_scalar_params(self):
            hdi = hdi_from_pdf(self, mass)
            lower_tail = float(f"{hdi[0]:{fmt}}")
            upper_tail = float(f"{hdi[1]:{fmt}}")
            return (lower_tail, upper_tail)
        else:
            return None

    def _check_endpoints(self, lower, upper, raise_error=True):
        """
        Evaluate if the lower and upper values are in the support of the distribution

        Parameters
        ----------
        lower : int or float
            lower endpoint
        upper : int or float
            upper endpoint
        raise_error : bool
            If True (default) it will raise ValueErrors, otherwise it will return True
            if the lower and upper endpoint are in the support of the distribution or
            False otherwise.
        """
        s_l, s_u = self.support

        if raise_error:
            domain_error = (
                f"The provided endpoints are outside the domain of the "
                f"{self.__class__.__name__} distribution"
            )

            if np.isfinite(s_l):
                if lower < s_l:
                    raise ValueError(domain_error)

            if np.isfinite(s_u):
                if upper > s_u:
                    raise ValueError(domain_error)
            if np.isfinite(s_l) and np.isfinite(s_u):
                if lower == s_l and upper == s_u:
                    raise ValueError(
                        "Given the provided endpoints, mass will be always 1. "
                        "Please provide other values"
                    )
            return None
        else:
            return lower >= s_l and upper <= s_u

    def _finite_endpoints(self, support):
        """
        Return finite endpoints even for unbounded distributions

        Parameters
        ----------
        support : str or tuple
            Available string options are "full" or "restricted".
        """
        if isinstance(support, tuple):
            lower_ep, upper_ep = support
        else:
            lower_ep, upper_ep = self.support

            if not np.isfinite(lower_ep) or support == "restricted":
                lower_ep = self.ppf(0.0001)
            if not np.isfinite(upper_ep) or support == "restricted":
                upper_ep = self.ppf(0.9999)

        return lower_ep, upper_ep

    def plot_pdf(
        self,
        moments=None,
        pointinterval=False,
        interval="hdi",
        levels=None,
        support="full",
        legend="legend",
        color=None,
        alpha=1,
        figsize=None,
        ax=None,
    ):
        """
        Plot the  pdf (continuous) or pmf (discrete).

        Parameters
        ----------
        moments : str
            Compute moments. Use any combination of the strings ``m``, ``d``, ``v``, ``s`` or ``k``
            for the mean (μ), standard deviation (σ), variance (σ²), skew (γ) or kurtosis (κ)
            respectively. Other strings will be ignored. Defaults to None.
        pointinterval : bool
            Whether to include a plot of the quantiles. Defaults to False. If True the default is to
            plot the median and two interquantiles ranges.
        interval : str
            Type of interval. Available options are highest density interval `"hdi"` (default),
        equal tailed interval `"eti"` or intervals defined by arbitrary `"quantiles"`.
        levels : list
            Mass of the intervals. For hdi or eti the number of elements should be 2 or 1.
            For quantiles the number of elements should be 5, 3, 1 or 0
            (in this last case nothing will be plotted).
        support : str:
            If ``full`` use the finite end-points to set the limits of the plot. For unbounded
            end-points or if ``restricted`` use the 0.001 and 0.999 quantiles to set the limits.
        legend : str
            Whether to include a string with the distribution and its parameter as a ``"legend"`` a
            ``"title"`` or not include them ``None``.
        color : str
            Valid matplotlib color. Defaults to None, colors will be selected from the active
            color cycle.
        alpha : float
            Transparency of the line. Defaults to 1 (no transparency).
        figsize : tuple
            Size of the figure
        ax : matplotlib axes
        """

        if valid_scalar_params(self):
            return plot_pdfpmf(
                self,
                moments,
                pointinterval,
                interval,
                levels,
                support,
                legend,
                color,
                alpha,
                figsize,
                ax,
            )
        else:
            return None

    def plot_cdf(
        self,
        moments=None,
        pointinterval=False,
        interval="hdi",
        levels=None,
        support="full",
        legend="legend",
        color=None,
        alpha=1,
        figsize=None,
        ax=None,
    ):
        """
        Plot the cumulative distribution function.

        Parameters
        ----------
        moments : str
            Compute moments. Use any combination of the strings ``m``, ``d``, ``v``, ``s`` or ``k``
            for the mean (μ), standard deviation (σ), variance (σ²), skew (γ) or kurtosis (κ)
            respectively. Other strings will be ignored. Defaults to None.
        pointinterval : bool
            Whether to include a plot of the quantiles. Defaults to False. If True the default is to
            plot the median and two interquantiles ranges.
        interval : str
            Type of interval. Available options are highest density interval `"hdi"` (default),
        equal tailed interval `"eti"` or intervals defined by arbitrary `"quantiles"`.
        levels : list
            Mass of the intervals. For hdi or eti the number of elements should be 2 or 1.
            For quantiles the number of elements should be 5, 3, 1 or 0
            (in this last case nothing will be plotted).
        support : str:
            If ``full`` use the finite end-points to set the limits of the plot. For unbounded
            end-points or if ``restricted`` use the 0.001 and 0.999 quantiles to set the limits.
        color : str
            Valid matplotlib color. Defaults to None, colors will be selected from the active
            color cycle.
        alpha : float
            Transparency of the line. Defaults to 1 (no transparency).
        legend : str
            Whether to include a string with the distribution and its parameter as a ``"legend"`` a
            ``"title"`` or not include them ``None``.
        figsize : tuple
            Size of the figure
        ax : matplotlib axes
        """
        if valid_scalar_params(self):
            return plot_cdf(
                self,
                moments,
                pointinterval,
                interval,
                levels,
                support,
                legend,
                color,
                alpha,
                figsize,
                ax,
            )
        else:
            return None

    def plot_ppf(
        self,
        moments=None,
        pointinterval=False,
        interval="hdi",
        levels=None,
        legend="legend",
        color=None,
        alpha=1,
        figsize=None,
        ax=None,
    ):
        """
        Plot the quantile function.

        Parameters
        ----------
        moments : str
            Compute moments. Use any combination of the strings ``m``, ``d``, ``v``, ``s`` or ``k``
            for the mean (μ), standard deviation (σ), variance (σ²), skew (γ) or kurtosis (κ)
            respectively. Other strings will be ignored. Defaults to None.
        pointinterval : bool
            Whether to include a plot of the quantiles. Defaults to False. If True the default is to
            plot the median and two interquantiles ranges.
        interval : str
            Type of interval. Available options are highest density interval `"hdi"` (default),
        equal tailed interval `"eti"` or intervals defined by arbitrary `"quantiles"`.
        levels : list
            Mass of the intervals. For hdi or eti the number of elements should be 2 or 1.
            For quantiles the number of elements should be 5, 3, 1 or 0
            (in this last case nothing will be plotted).
        legend : str
            Whether to include a string with the distribution and its parameter as a ``"legend"`` a
            ``"title"`` or not include them ``None``.
        color : str
            Valid matplotlib color. Defaults to None, colors will be selected from the active
            color cycle.
        alpha : float
            Transparency of the line. Defaults to 1 (no transparency).
        figsize : tuple
            Size of the figure
        ax : matplotlib axes
        """
        if valid_scalar_params(self):
            return plot_ppf(
                self, moments, pointinterval, interval, levels, legend, color, alpha, figsize, ax
            )
        else:
            return None

    def plot_interactive(
        self,
        kind="pdf",
        xy_lim="both",
        pointinterval=True,
        interval="hdi",
        levels=None,
        figsize=None,
    ):
        """
        Interactive exploration of distributions parameters

        Parameters
        ----------
        kind : str:
            Type of plot. Available options are `pdf`, `cdf` and `ppf`.
        xy_lim : str or tuple
            Set the limits of the x-axis and/or y-axis.
            Defaults to `"both"`, the limits of both axis are fixed.
            Use `"auto"` for automatic rescaling of x-axis and y-axis.
            Or set them manually by passing a tuple of 4 elements,
            the first two for x-axis, the last two for y-axis. The tuple can have `None`.
        pointinterval : bool
            Whether to include a plot of the quantiles. Defaults to False. If True the default is to
            plot the median and two interquantiles ranges.
        interval : str
            Type of interval. Available options are highest density interval `"hdi"` (default),
        equal tailed interval `"eti"` or intervals defined by arbitrary `"quantiles"`.
        levels : list
            Mass of the intervals. For hdi or eti the number of elements should be 2 or 1.
            For quantiles the number of elements should be 5, 3, 1 or 0
            (in this last case nothing will be plotted).
        figsize : tuple
            Size of the figure
        """
        check_inside_notebook()

        if valid_scalar_params(self, check_frozen=False):
            args = dict(zip(self.param_names, self.params))
        else:
            args = init_vals[self.__class__.__name__]

        self.__init__(**args)  # pylint: disable=unnecessary-dunder-call

        if xy_lim == "both":
            xlim = self._finite_endpoints("full")
            xvals = self.xvals("restricted")
            if kind == "pdf":
                max_pdf = np.max(self.pdf(xvals))
                ylim = (-max_pdf * 0.075, max_pdf * 1.5)
            elif kind == "ppf":
                max_ppf = self.ppf(0.999)
                ylim = (-max_ppf * 0.075, max_ppf * 1.5)
        elif isinstance(xy_lim, tuple):
            xlim = xy_lim[:2]
            ylim = xy_lim[2:]

        sliders = {}
        if self.__class__.__name__ == "Categorical":
            pointinterval = False
            name = self.param_names[0]
            params = self.params[0]
            names = [f"{name}_{i}" for i in range(len(params))]
            supports = [(0, 1) for _ in range(len(params))]

            for name, value, support in zip(names, params, supports):
                sliders[name] = get_slider(name, value, *support)
        else:
            for name, value, support in zip(self.param_names, self.params, self.params_support):
                sliders[name] = get_slider(name, value, *support)

        def plot(**args):  # pylint: disable=inconsistent-return-statements
            if self.__class__.__name__ == "Categorical":
                values = list(args.values())
                args = {list(args.keys())[0].split("_")[0]: values}
                if np.sum(values) > 1:
                    return None

            self.__init__(**args)  # pylint: disable=unnecessary-dunder-call

            if kind == "pdf":
                ax = self.plot_pdf(
                    legend=False,
                    pointinterval=pointinterval,
                    interval=interval,
                    levels=levels,
                    figsize=figsize,
                )
            elif kind == "cdf":
                ax = self.plot_cdf(
                    legend=False,
                    pointinterval=pointinterval,
                    interval=interval,
                    levels=levels,
                    figsize=figsize,
                )
            elif kind == "ppf":
                ax = self.plot_ppf(
                    legend=False,
                    pointinterval=pointinterval,
                    interval=interval,
                    levels=levels,
                    figsize=figsize,
                )
            if xy_lim != "auto" and kind != "ppf":
                ax.set_xlim(*xlim)
            if xy_lim != "auto" and kind != "cdf":
                ax.set_ylim(*ylim)

        return interactive(plot, **sliders)


class Continuous(Distribution):
    """Base class for continuous distributions."""

    def __init__(self):
        super().__init__()
        self.kind = "continuous"

    def xvals(self, support):
        """Provide x values in the support of the distribution. This is useful for example when
        plotting.

        Parameters
        ----------
        support : str
            Available options are "full" or "restricted".
        """
        lower_ep, upper_ep = self._finite_endpoints(support)
        x_vals = np.linspace(lower_ep, upper_ep, 1000)
        return x_vals

    def _fit_mle(self, sample, **kwargs):
        """
        Estimate the parameters of the distribution from a sample by maximizing the likelihood.

        Parameters
        ----------
        sample : array-like
            a sample
        kwargs : dict
            keywords arguments passed to scipy.stats.rv_continuous.fit
        """
        raise NotImplementedError

    def pdf(self, x, *args, **kwds):
        """Probability density function at x.

        Parameters
        ----------
        x : array_like
            Values on which to evaluate the pdf
        """
        return self.rv_frozen.pdf(x, *args, **kwds)

    def logpdf(self, x, *args, **kwds):
        """Probability mass function at x.

        Parameters
        ----------
        x : array_like
            Values on which to evaluate the pdf
        """
        return self.rv_frozen.logpdf(x, *args, **kwds)


class Discrete(Distribution):
    """Base class for discrete distributions."""

    def __init__(self):
        super().__init__()
        self.kind = "discrete"

    def xvals(self, support):
        """Provide x values in the support of the distribution. This is useful for example when
        plotting.
        """
        lower_ep, upper_ep = self._finite_endpoints(support)
        x_vals = np.arange(lower_ep, upper_ep + 1, dtype=int)
        return x_vals

    def pdf(self, x, *args, **kwds):
        """Probability mass function at x.

        Parameters
        ----------
        x : array_like
            Values on which to evaluate the pdf
        """
        return self.rv_frozen.pmf(x, *args, **kwds)

    def logpdf(self, x, *args, **kwds):
        """Probability mass function at x.

        Parameters
        ----------
        x : array_like
            Values on which to evaluate the pdf
        """
        return self.rv_frozen.logpmf(x, *args, **kwds)
