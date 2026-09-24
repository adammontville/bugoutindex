# Grid outages and energy stress

**Status:** Incubating — theoretical exploration (Adam Montville, 2026-09-23).

**Not in the BugOut Index.** No weight. No weekly wiring. No production series has been chosen. `runtime/data/fetch/fetch_grid_outages.py` is fail-closed (`NOT_WIRED`): calling it raises, and it does not return a sample outage figure. The weekly publisher does not import it.

This note is the research brief. It is not a methodology version and not a claim that a grid measure is ready to publish.

The BugOut Index is a directional weekly stress reading of published statistics about observed U.S. conditions. It is not a forecast and not a historical bug-out siren. A grid idea earns a place beside the score only if it improves that reading. Companions stay outside the score unless a later, explicit methodology version says otherwise.

---

## Why this stays incubating

The 2026-09-23 inventory cut parked air quality, healthcare capacity, and natural-disaster frequency. Grid outages was called out to **stay**. The public argument around electricity has become specific enough that the project should know which measures exist, and which of them would actually help, before anyone writes a fetcher.

That is a documentation decision. It is not permission to score electricity, data-center load, or a geopolitical fuel story.

## Why it matters now

Three conversations are easy to mash into one “energy” tile. They are different objects. None of them is an input.

**Bulk-system stress is an observed operating problem, on a planning cadence.** NERC’s seasonal reliability assessments, Long-Term Reliability Assessment, and State of Reliability discuss planning reserve margins and actual energy emergencies as related but distinct facts: a forward view of whether resources cover peak demand, versus emergency alerts when an interconnection is already short. Those documents are how the U.S. reliability regulator describes grid stress. They are not a Friday national statistic of societal conditions.

**Data-center and AI load is a demand debate.** Periodic studies — Lawrence Berkeley National Laboratory’s United States Data Center Energy Usage Report, International Energy Agency electricity and AI work, and the electricity chapters of EIA’s Annual Energy Outlook and Short-Term Energy Outlook — argue about how fast large new loads show up in utility forecasts and interconnection queues. There is no public weekly series of national “AI electricity stress” that this repository should pretend to publish. Load growth, if it changes prices or reliability in a measured way, would show up in one of the candidate series below, not in a slogan.

**Energy geopolitics is context.** Fuel-price shocks, export restrictions, and war-related oil and gas moves can tighten the fuels generators burn, and they can move consumer prices. When those price effects are national and published, they already have a path into the index through CPI-U inflation. They are not a second inflation weight, and they are not an outage series. This note does not score geopolitics.

## Usefulness criteria

A candidate is worth a shadow companion only if it would improve a **directional weekly stress reading of observed societal conditions**. It fails that test, and stays in this note, when the honest description is one or more of these:

| Failure | What it looks like here |
| --- | --- |
| Event noise | A storm, a single-utility failure, or a two-day wholesale spike that mean-reverts without a change in the national condition the index is about. |
| Regional | One interconnection, one ISO, or one state, presented as if it were the U.S. reading. The index is national. |
| Laggy | An annual yearbook that cannot move a weekly page without a fake timestamp. |
| Overlapping inflation or debt | Electricity already inside CPI-U, or a capital-spending story that debt-to-GDP is not measuring either. A second copy of inflation is not new information. |

Gates that all have to be true before a shadow tile, and long before any weight discussion:

1. **Directional.** A sustained move would change a reader’s view of observed U.S. conditions, not merely record that an event happened.
2. **Geography is explicit.** National, or labeled regional and kept off the headline number.
3. **Cadence is honest.** Either the series updates often enough to be a weekly reading, or it is labeled as an annual companion the way other annual inputs are. No invented fetch time.
4. **Non-overlap.** It is not a restatement of CPI inflation, unemployment, or debt-to-GDP.
5. **A named public source.** A specific table or form, with the observation date the publisher would store. No interpolated national total.
6. **Fail-closed.** A missing source omits the companion. It never fills a number, and it never blocks the six-metric publish.

## Candidate measures to research

These are research leads. None is selected. None is wired.

### 1. Major disturbance events (DOE-417, republished by EIA)

- **Source:** [Form DOE-417](https://doe417.energy.gov/), Electric Emergency Incident and Disturbance Report. DOE collects the filings for emergency awareness. EIA uses the same incidents in monthly electric-power reporting, including the [Electric Power Monthly](https://www.eia.gov/electricity/monthly/).
- **What it measures:** Qualifying emergencies and disturbances (major outages, load shedding, and related events), filed by the responsible entity. This is an event list, not a customer-minute index.
- **Cadence:** Event-driven filings; monthly republication.
- **Usefulness:** A count of major disturbances behaves like a crisis overlay. Geography is the reporting utility or balancing authority. Weather clusters dominate. A week with no filing is not “high stability,” and several filings in one state are not a national regime change. The open research question is whether any trailing, clearly defined rate can be built from the public event list without inventing a national index the agencies do not publish. Until that definition is written down and sourced, a raw event count does not belong beside the score, and it does not belong in it.

### 2. SAIDI / SAIFI-style reliability (EIA-861)

- **Source:** Form EIA-861, Annual Electric Power Industry Report, reliability schedules. National history is Electric Power Annual [Table 11.1](https://www.eia.gov/electricity/annual/html/epa_11_01.html). Respondent-level files are on the [EIA-861 page](https://www.eia.gov/electricity/data/eia861/).
- **What it measures:** SAIDI is minutes of non-momentary interruption per year for the average customer. SAIFI is how many such interruptions that customer experienced. CAIDI is the average restoration time. EIA publishes IEEE 1366 results and an “any method” combination, with and without major event days, and with loss-of-supply outages removed or kept. Those cuts are not interchangeable.
- **Cadence:** Annual, with a lag after the calendar year.
- **Usefulness:** This is the right family of concepts for “are customers losing power more often or for longer,” and the summary table is national. It is a poor weekly directional series. A Friday page cannot honestly move on a number that updates once a year. Mixing IEEE and non-IEEE respondents, or folding major-event days back in, changes the level. The research question is narrower: whether one stated annual series (for example national SAIDI without major event days, one method, with its coverage note) is worth a stale companion tile, labeled with the report year, the way other annual figures are labeled. That is still not a weekly score input.

### 3. Reserve margin and capacity forecasts

- **Source:** NERC Long-Term Reliability Assessment and the summer and winter seasonal assessments (Anticipated Reserve Margin against each assessment area’s Reference Margin Level). NERC’s State of Reliability treats planning reserve margins and Energy Emergency Alerts as different objects: one is forward resource adequacy, the other is an emergency that already occurred. EIA’s [Short-Term Energy Outlook](https://www.eia.gov/outlooks/steo/) electricity chapter forecasts generation and consumption; it is not an outage series.
- **What it measures:** Whether planners expect resources to cover seasonal peak demand, by assessment area. Not how many customers were out this week.
- **Cadence:** Seasonal or annual for NERC assessments. STEO is monthly and is a forecast.
- **Usefulness:** A tight planning margin is a statement about the future. The index’s claim is published statistics of current conditions, not a prediction. Putting a reserve margin in the score would turn the product into a forecast. The geography is also an assessment area, not the United States. Acceptable use, later, is a dated context note that quotes a NERC sentence and links the assessment. That note would still have no weight.

### 4. Wholesale price spikes as stress proxies

- **Source:** EIA [wholesale electricity market data](https://www.eia.gov/electricity/wholesale/). The underlying prices are the public ISO and RTO markets (PJM, ERCOT, CAISO, MISO, NYISO, ISO-NE). There is no single national wholesale price.
- **What it measures:** Locational or hub prices. Spikes are often weather, fuel, or an outage in that market.
- **Cadence:** Hourly in the ISOs; EIA’s wholesale tables are a published aggregate on EIA’s own calendar.
- **Usefulness:** Retail electricity is already inside CPI-U, which the inflation fetcher rolls into the core score through FRED `CPIAUCSL`. A wholesale spike that never reaches the CPI print is a market event. A spike that does reach CPI is already inside inflation. That is the overlap problem, plus the regional problem, plus event noise. A sustained, named EIA aggregate could be researched later as a companion only if it is dated, sourced, and shown as not in the score. It is not a weight candidate while CPI-U remains a core input.

### 5. Data-center load and interconnection queues

- **Source:** No citable public weekly national series of data-center electricity use. The public record is periodic: Lawrence Berkeley National Laboratory’s data-center energy usage report, IEA electricity and AI reports, and utility integrated resource plans. Interconnection queues are compiled annually by Lawrence Berkeley National Laboratory in the *Queued Up* series (generation projects, and large loads where the edition reports them). High-frequency grid operations, which are not load-by-customer-type, are EIA-930 via the [Hourly Electric Grid Monitor](https://www.eia.gov/electricity/gridmonitor/about): balancing-authority demand, generation, and interchange.
- **What it measures:** Studies measure estimated data-center consumption or a scenario. *Queued Up* measures a planning backlog, including projects that may never be built. EIA-930 measures how much electricity balancing authorities reported moving, not whether society was under more stress.
- **Cadence:** Annual or irregular for the studies and the queue report. Hourly for EIA-930.
- **Usefulness:** These explain why reserve margins and queues are in the news. They are not scored inputs. EIA-930 can show that a region’s demand was high; a hot afternoon is also a normal summer. Queue length is not observed customer harm. Do not invent an “AI load” number, and do not cite a study’s headline terawatt-hour figure as if the weekly job had measured it.

## Incubation path

1. **Theory.** This note. No score change, no fetcher that succeeds.
2. **Source feasibility.** Pick at most one candidate. Write the exact table, the geography, the lag, the method cut (for SAIDI), and the overlap with CPI. Still no `status: success`.
3. **Shadow companion.** A real fetcher, an observation date, and a source link. No weight. Not in `CORE_METRICS` or `compute_index`. A failed fetch does not abort the weekly publish. The same rule the labor-utilization shadow already follows.
4. **Weight discussion, only after that, and only as a versioned methodology change.** A backtest would have to show a better directional reading of observed conditions, not a better chart of storms. The default is that this step does not happen. v1.0.0 stays the published score until that version exists.

## What is explicitly out of scope

- No change to the live score, bands, weights, or `compute_index`.
- No weekly publish of a grid series.
- No sample success from `fetch_grid_outages`.
- No claim that any candidate above is production-ready.
- Energy geopolitics, AI load, and reserve-margin forecasts are context for the research. They are not hidden inputs.
