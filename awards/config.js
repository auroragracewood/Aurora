/* ============================================================
   Aurora Awards — config
   ============================================================
   Locked 2026-05-05. Categories: 9 main + 1 influencer +
   Community Choice (bonus track, points-based, no physical
   trophy). Pricing: Main $199/$299/$399, Influencer $99/$149/$199.
   Best Micro-Influencer removed. Community Choice removed from
   main awards array (handled separately).
   See awards/CLAUDE.md "AWARDS STRUCTURE & ECONOMICS" section
   for full rationale.
   ============================================================ */

const AURORA_CONFIG = {
  /* ---- Award categories displayed on /awards/ as cards ---- */
  awards: [
    /* Main Awards track — 9 categories, crystal trophy each */
    { title: "Best Overall Website: North Star Award", track: "main", tier: "Pinnacle", description: "For the strongest complete website across design, clarity, usability, brand, and conversion intent.", meta: "Ideal badge use: homepage footer, press page, proposal decks." },
    { title: "High Performer: Northern Lights Award", track: "main", tier: "Performance", description: "For websites, campaigns, or creator brands with strong measurable traction and standout execution.", meta: "Evidence: analytics, conversion data, audience growth, testimonials." },
    { title: "Best UX/UI: Clear Sky Award", track: "main", tier: "Design", description: "For clean navigation, polished interface systems, accessibility awareness, and frictionless user journeys.", meta: "Evidence: screenshots, flow notes, accessibility notes, UX outcomes." },
    { title: "Best Brand Identity: Spectrum Award", track: "main", tier: "Brand", description: "For cohesive visual language, voice, positioning, and memorable presentation across digital touchpoints.", meta: "Evidence: brand guide, website URL, social/profile examples." },
    { title: "Most Innovative Campaign: Solar Flare Award", track: "main", tier: "Marketing", description: "For bold marketing ideas with original mechanics, creative reach, and clear audience response.", meta: "Evidence: campaign summary, assets, results, audience reaction." },
    { title: "Best Social Presence: Signal Glow Award", track: "main", tier: "Social", description: "For brands or creators using social platforms with consistency, clarity, personality, and measurable engagement.", meta: "Evidence: profile links, growth data, standout posts, engagement proof." },
    { title: "Best Launch: First Light Award", track: "main", tier: "Launch", description: "For new websites, brands, campaigns, or creator platforms with an impressive first public showing.", meta: "Evidence: launch date, launch goals, early results, launch assets." },
    { title: "Best Marketing Website: Aurora Funnel Award", track: "main", tier: "Conversion", description: "For websites designed to explain, persuade, and convert without losing style or trust.", meta: "Evidence: conversion goals, CTA flow, analytics, landing-page results." },
    { title: "Best Purpose-Driven Campaign: Horizon Award", track: "main", tier: "Impact", description: "For campaigns that combine marketing execution with public benefit, advocacy, education, or positive cultural impact.", meta: "Evidence: mission, outcomes, partnerships, reach, public response." },
    /* Influencer Awards track — 1 category, larger acrylic trophy */
    { title: "Top Emerging Influencer: Rising Star Award", track: "influencer", tier: "Influence", description: "For a creator building visible momentum, strong niche identity, and meaningful audience connection.", meta: "Evidence: creator profile links, audience data, campaign proof." }
  ],

  /* ---- Submission paths (form panels in the accordion) ---- */
  submissionTypes: [
    {
      id: "award-entry",
      title: "Award Entry Submission",
      subtitle: "Apply for any of the 9 main award categories.",
      price: "$199 early / $299 standard / $399 late",
      intro: "Submit your work for review against one main category. Earn an award badge to display on your site as proof your work has been recognized.",
      fields: [
        ["company_name", "Company / Brand / Creator Name", "text", true],
        ["contact_email", "Contact Email", "email", true],
        ["public_url", "Website or Public Profile URL", "url", true],
        ["award_category", "Award Category", "select", true, ["Best Overall Website", "High Performer", "Best UX/UI", "Best Brand Identity", "Most Innovative Campaign", "Best Social Presence", "Best Launch", "Best Marketing Website", "Best Purpose-Driven Campaign"]],
        ["project_summary", "Project Summary", "textarea", true],
        ["proof_metrics", "Proof / Metrics / Results", "textarea", true],
        ["asset_links", "Asset Links", "textarea", false],
        ["preferred_badge_name", "Preferred Display Name for Badge", "text", false]
      ],
      requirements: ["Working public URL", "Applicant has authority to submit", "Clear project summary", "Proof of quality, impact, or audience response", "Entry fee paid before review", "Recognition not guaranteed — paid review only"]
    },
    {
      id: "influencer-entry",
      title: "Influencer Award Entry",
      subtitle: "Apply for the Top Emerging Influencer (Rising Star) award.",
      price: "$99 early / $149 standard / $199 late",
      intro: "For creators building momentum and meaningful audience connection. Submit your creator profile and audience data for review against the Rising Star rubric.",
      fields: [
        ["creator_name", "Creator Name", "text", true],
        ["contact_email", "Contact Email", "email", true],
        ["primary_platform_url", "Primary Platform Profile URL", "url", true],
        ["other_platform_urls", "Other Platform URLs", "textarea", false],
        ["niche", "Niche / Vertical", "text", true],
        ["audience_summary", "Audience Summary (size, growth, engagement)", "textarea", true],
        ["highlight_work", "Highlighted Work / Best Pieces", "textarea", true],
        ["partnership_examples", "Partnership / Collaboration Examples", "textarea", false],
        ["preferred_badge_name", "Preferred Display Name for Badge", "text", false]
      ],
      requirements: ["Active public creator profile", "Applicant has authority to submit", "Real audience metrics (no purchased follows)", "Niche or vertical clearly identified", "Entry fee paid before review", "Recognition not guaranteed — paid review only"]
    },
    {
      id: "community-choice",
      title: "Community Choice (bonus points track)",
      subtitle: "Earn points toward the Community Choice award. No physical trophy — public mention recognition.",
      price: "$25 bundled at any cat sub (max 10 per cat sub) / $49 direct submission / Free via social-vote",
      intro: "Community Choice is a points-based bonus award with no physical trophy. Earn points by adding bundled CC at any category submission ($25 each, 75 points each, max 10 bundled per cat sub), or by direct CC submission ($49 each, 50 points each, unlimited), or by getting fans to sign in with their platform account and vote (1 point per linked account per brand per cycle, free). Highest tally at year-end earns the Polaris Award. Full leaderboard mechanics ship in a future release.",
      fields: [
        ["brand_name", "Brand / Creator / Project Name", "text", true],
        ["contact_email", "Contact Email", "email", true],
        ["public_url", "Public URL", "url", true],
        ["why_community", "Why your community supports you", "textarea", true]
      ],
      requirements: ["Working public URL", "Applicant has authority to submit", "No physical trophy — digital badge + public mention only", "Highest point tally at year-end wins", "Anti-fraud monitoring applies — coordinated sock-puppet voting will be disqualified"]
    },
    {
      id: "editorial-coverage",
      title: "Editorial Coverage Request",
      subtitle: "Request a feature, interview, spotlight, roundup, or case-study review.",
      price: "$249 review fee",
      intro: "For companies, creators, or agencies that want Aurora Gracewood to consider them for editorial coverage or public spotlight content.",
      fields: [
        ["name", "Company / Creator Name", "text", true],
        ["email", "Contact Email", "email", true],
        ["url", "Primary URL", "url", true],
        ["coverage_type", "Coverage Type", "select", true, ["Feature Article", "Founder Interview", "Campaign Breakdown", "Website Review", "Influencer Spotlight", "Agency Spotlight"]],
        ["story_angle", "Story Angle", "textarea", true],
        ["why_now", "Why This Should Be Covered Now", "textarea", true],
        ["press_links", "Press Kit / Media Links", "textarea", false]
      ],
      requirements: ["Public project or brand", "Clear story angle", "Media assets or links preferred", "Review fee paid", "Coverage is not guaranteed"]
    },
    {
      id: "directory-listing",
      title: "Directory Listing Application",
      subtitle: "Apply to be listed as a recommended agency, creator, tool, platform, or service.",
      price: "$99 application fee",
      intro: "For businesses that want inclusion in the Aurora directory after quality review.",
      fields: [
        ["listing_name", "Listing Name", "text", true],
        ["email", "Contact Email", "email", true],
        ["website", "Website URL", "url", true],
        ["listing_type", "Listing Type", "select", true, ["Design Agency", "Marketing Agency", "Influencer / Creator", "SaaS Tool", "Consultant", "Production Studio", "Ecommerce Brand", "Other"]],
        ["short_description", "Short Directory Description", "textarea", true],
        ["services", "Services / Specialties", "textarea", true],
        ["proof", "Proof of Quality", "textarea", false]
      ],
      requirements: ["Legitimate public website", "Clear services or identity", "No misleading claims", "Application fee paid", "Directory placement is reviewed before approval"]
    },
    {
      id: "sponsor-inquiry",
      title: "Sponsor Inquiry",
      subtitle: "For brands that want visibility across award pages, cycles, winner features, or reports.",
      price: "Custom quote",
      intro: "For companies that want to sponsor categories, winner announcements, newsletters, reports, or digital editorial content.",
      fields: [
        ["org_name", "Organization Name", "text", true],
        ["email", "Contact Email", "email", true],
        ["website", "Website URL", "url", true],
        ["interest", "Sponsorship Interest", "select", true, ["Category Sponsor", "Newsletter Sponsor", "Winner Page Sponsor", "Annual Report Sponsor", "Custom Partnership"]],
        ["budget", "Estimated Budget Range", "select", false, ["Under $1,000", "$1,000–$5,000", "$5,000–$15,000", "$15,000+", "Not sure yet"]],
        ["goals", "Goals", "textarea", true]
      ],
      requirements: ["Relevant brand fit", "Clear sponsorship goal", "No conflict with judging integrity", "Custom quote after review"]
    }
  ]
};
