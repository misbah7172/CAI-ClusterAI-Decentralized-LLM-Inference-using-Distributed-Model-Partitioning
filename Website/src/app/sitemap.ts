import { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://Cai-runtime.vercel.app"; // placeholder or production URL
  const routes = [
    "",
    "/architecture",
    "/sandbox",
    "/energy",
    "/distributed-ai",
    "/studio",
    "/remote-cluster",
    "/research",
    "/benchmarks",
    "/models",
    "/download",
    "/roadmap",
  ];

  return routes.map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: route === "" ? 1.0 : 0.8,
  }));
}
