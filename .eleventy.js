const { DateTime } = require("luxon");

module.exports = function (eleventyConfig) {
  // Copy the old Drupal files directory straight through so existing
  // image/attachment references in post bodies keep working unchanged.
  eleventyConfig.addPassthroughCopy("sites");

  // New hand-written posts going forward should drop images here.
  eleventyConfig.addPassthroughCopy("images");

  // Optional: your own stylesheet.
  eleventyConfig.addPassthroughCopy("css");

  eleventyConfig.addFilter("readableDate", (dateObj) => {
    return DateTime.fromJSDate(dateObj, { zone: "utc" }).toFormat("dd LLL yyyy");
  });

  // For raw Unix timestamps (seconds), like the comment "created" field,
  // which isn't a front-matter `date` key so Eleventy never turns it into
  // a JS Date automatically.
  eleventyConfig.addFilter("epochDate", (epochSeconds) => {
    return DateTime.fromSeconds(epochSeconds, { zone: "utc" }).toFormat("dd LLL yyyy");
  });

  // Simple slugify -- no external dependency needed. Handles tags with
  // spaces (e.g. "regular expressions") or punctuation (e.g. "c++").
  eleventyConfig.addFilter("limit", (arr, n) => arr.slice(0, n));

  eleventyConfig.addFilter("slug", (str) => {
    return String(str)
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  });

  // All generated posts, regardless of tags -- used for the chronological
  // index page. Glob is relative to the project root, not dir.input.
  eleventyConfig.addCollection("posts", (collectionApi) => {
    return collectionApi.getFilteredByGlob("posts/*.html");
  });

  // Same as above, but restricted to nodeType: story -- for the main
  // index page, which should only show blog-style posts, not static
  // pages or the source_code nodes.
  eleventyConfig.addCollection("storyPosts", (collectionApi) => {
    return collectionApi
      .getFilteredByGlob("posts/*.html")
      .filter((item) => item.data.nodeType === "story");
  });

  // Unique sorted list of every tag in use, for the tag-browsing pages.
  eleventyConfig.addCollection("tagList", (collectionApi) => {
    const tagSet = new Set();
    collectionApi.getAll().forEach((item) => {
      if (Array.isArray(item.data.tags)) {
        item.data.tags.forEach((tag) => tagSet.add(tag));
      }
    });
    return [...tagSet].sort();
  });

  return {
    dir: {
      input: "posts",
      includes: "../_includes",
      data: "../_data",
      output: "../_site",
    },
    templateFormats: ["html", "njk"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
};
