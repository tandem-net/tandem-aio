/**
 * Next.js configuration.
 * ----------------------------------------------------------------------------
 * Intentionally minimal. The App Router (the `app/` directory) is enabled by
 * default in Next 13+, so there is nothing to flip on here. We enable
 * `reactStrictMode` to surface side-effect bugs (double-invoked effects in dev)
 * early — important because several of our components run scroll listeners and
 * animation loops that must clean themselves up correctly.
 */
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
