import numpy as np
import scipy.integrate as scint
from . import sv_abc as sv


class GarchApproxUncor(sv.SvABC):
    """
    The implementation of Barone-Adesi et al. (2004)'s approximation pricing formula for European
    options under uncorrelated GARCH diffusion model.

    References: Barone-Adesi, G., Rasmussen, H., Ravanelli, C., 2005. An option pricing formula for the GARCH diffusion model. Computational Statistics & Data Analysis, 2nd CSDA Special Issue on Computational Econometrics 49, 287–310. https://doi.org/10.1016/j.csda.2004.05.014

    This method is only used to compare with the method GarchCondMC.
    """


class GarchCondMC(sv.SvABC, sv.CondMcBsmABC):
    """
    Garch model with conditional Monte-Carlo simulation
    The SDE of SV is: dv_t = mr * (theta - v_t) dt + vov * v_t dB_T
    """

    var_process = True

    def vol_paths(self, tobs):
        """
        Milstein Schemes:
        w_(t+dt) = w_t + (mr * theta * exp(-w_t) - mr - vov^2 / 2) * dt + vov * Z * sqrt(dt)
        v_t = exp(w_t)
        Args:
            mr: coefficient of dt
            theta: the long term average
            Z : std normal distributed RN
            dt : delta t, time step

        Returns: Variance path (time, path) including the value at t=0
        """
        n_dt = len(tobs)
        n_path = self.n_path
        rn_norm = self._bm_incr(tobs=np.arange(1, n_dt + 0.1), cum=False)

        w_t = np.zeros((n_dt + 1, int(n_path)))
        w_t[0, :] = 2 * np.log(self.sigma)

        for i in range(1, n_dt + 1):
            w_t[i, :] = (
                w_t[i - 1, :]
                + (
                    self.mr * self.theta * np.exp(-w_t[i - 1, :])
                    - self.mr
                    - self.vov ** 2 / 2
                )
                * self.dt
                + self.vov * np.sqrt(self.dt) * rn_norm[i - 1, :]
            )

        return np.exp(w_t)

    def cond_spot_sigma(self, texp):

        rhoc = np.sqrt(1.0 - self.rho ** 2)
        tobs = self.tobs(texp)
        n_dt = len(tobs)
        var_paths = self.vol_paths(tobs)
        sigma_paths = np.sqrt(var_paths)
        sigma_final = sigma_paths[-1, :]
        int_sigma = scint.simps(sigma_paths, dx=1, axis=0) * texp/n_dt
        int_var = scint.simps(var_paths, dx=1, axis=0) * texp/n_dt
        int_sigma_inv = scint.simps(1/sigma_paths, dx=1, axis=0) * texp/n_dt

        fwd_cond = np.exp(
            self.rho
            * (
                2 * (sigma_final - self.sigma) / self.vov
                - self.mr * self.theta * int_sigma_inv / self.vov
                + (self.mr / self.vov + self.vov / 4) * int_sigma
                - self.rho * int_var / 2
            )
        )  # scaled by initial value

        sigma_cond = rhoc * np.sqrt(int_var)

        return fwd_cond, sigma_cond
