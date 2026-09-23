[![AGPL License](https://img.shields.io/badge/license-AGPL%20v3-blue)](./LICENSE)
[![Commercial License](https://img.shields.io/badge/license-Commercial-orange)](./COMMERCIAL_LICENSE.md)

# BugOutIndex

The **BugOutIndex** is a societal stability scoring system designed to help individuals and communities anticipate critical points of instability. It turns published U.S. economic, crime, and governance statistics into a single score for current conditions.

**Live site:** <https://www.bugoutindex.com/> (also <https://adammontville.github.io/bugoutindex/>) — updated every Friday evening after US markets close.

**Weekly pipeline:** See [`runtime/publish/README.md`](./runtime/publish/README.md) for how the automated weekly update works.

**Architecture and roadmap:** See [`ARCHITECTURE_AND_ROADMAP.md`](./ARCHITECTURE_AND_ROADMAP.md) for how the score is produced, where the docs disagree, and a proposed Now / Next / Later plan. That document does not change the calculation.

## **How It Works**
1. **Metrics Analysis**: The published score uses six indicators: inflation, violent-plus-property crime, unemployment, debt-to-GDP, homelessness, and Edelman trust in government.
2. **Scoring Methodology**: Each metric is normalized, weighted, and aggregated to produce a comprehensive stability score.
3. **Actionable Insights**: The BugOutIndex helps users identify early warning signs of societal instability and make informed decisions about preparation or evacuation.

For detailed information on the metrics and methodology, see the [Metrics Documentation](./METRICS.md).

## **Contributing**
Contributions are welcome! Whether you're improving scoring logic, refining metrics, or suggesting new features, please review our [Contributing Guidelines](./CONTRIBUTING.md).

## License
BugOutIndex is available under a dual-license model:

1. **GNU Affero General Public License v3.0 (AGPL-3.0)**:
   - This license applies to open-source use.
   - You are free to use, modify, and distribute the software under the terms of the AGPL-3.0.
   - Full license text is available in the [LICENSE](./LICENSE.md) file.

2. **Commercial License**:
   - For proprietary or commercial use cases (e.g., integrating BugOutIndex into closed-source systems or SaaS platforms), a commercial license is required.
   - Read [COMMERCIAL_LICENSE](./COMMERCIAL_LICENSE.md) for more detail or contact [adam.w.montville@gmail.com] to inquire.

By contributing to this project, you agree to license your contributions under both the AGPL-3.0 and the commercial license.


---

BugOutIndex aims to empower individuals with the tools they need to better understand and navigate societal challenges. Let’s build a more prepared future—together.