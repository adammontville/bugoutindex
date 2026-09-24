[![AGPL License](https://img.shields.io/badge/license-AGPL%20v3-blue)](./LICENSE)
[![Commercial License](https://img.shields.io/badge/license-Commercial-orange)](./COMMERCIAL_LICENSE.md)

# BugOutIndex

The **BugOutIndex** is a directional reading of U.S. stress and stability. It places six published statistics between fixed endpoints so a reader can see how hard those conditions are pressing. Higher is more stable. It is not a forecast, and it is not an instruction to bug out.

**Live site:** <https://www.bugoutindex.com/> (also <https://adammontville.github.io/bugoutindex/>) — updated every Friday evening after US markets close.

**Weekly pipeline:** See [`runtime/publish/README.md`](./runtime/publish/README.md) for how the automated weekly update works.

**Architecture and roadmap:** See [`ARCHITECTURE_AND_ROADMAP.md`](./ARCHITECTURE_AND_ROADMAP.md) for how the score is produced, where the docs disagree, and the decided product framing. That document does not change the calculation.

## **How It Works**
1. **Six published inputs**: inflation, crime, unemployment, debt-to-GDP, homelessness, and trust in government. Markets, the short-term pulse, labor utilization, and food prices are companions. They are not in the score.
2. **Scoring**: Each of the six is normalized between fixed endpoints, weighted, and aggregated into one 0–100 score (methodology 1.0.0). Higher is more stable.
3. **What the score is for**: a weekly reading of pressure in those statistics. It does not say when to leave.

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

The weekly site and the methodology page are the public description of the index.