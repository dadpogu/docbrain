# Process: Thermolysis Pot Cycle
**Process ID:** P-001  
**Version:** 1.1 (Draft for approval)  
**Owner:** Facility Manager  
**Approver:** Operations Director  
**Last Reviewed:** 2026-10-02  
**Next Review:** 12 months after approval, or earlier following material change, incident, audit finding or licence change

> [!NOTE]
> This process sits under the [Integrated Operations Manual FOM-001](../manuals/op-manual.md) §7.6 (Batch preparation and processing). Values marked **[TBC]** must be confirmed by the Facility Manager (and the plant manufacturer where relevant) before approval. The original draft process steps are kept in [Appendix A](#appendix-a-original-draft-process-steps).

## 1. Purpose
To convert approved plastic feedstock into recovered hydrocarbon fractions (H1–H4), char and non-condensable gas through a controlled batch thermolysis cycle. The cycle must:
- give consistent, traceable product that meets specification;
- keep air emissions, odour, spills and waste within licence conditions, and prevent pollution;
- protect workers from heat, flammable gases, suspended loads and hazardous substances;
- return H4 to the next batch, recover char, and keep resource use per tonne as low as practicable.

## 2. Scope
**Included:** the full pot cycle at the Wodonga facility, from opening the lid of a used pot through cleaning, loading, sealing, kiln placement, the thermolysis run (normal and emergency shutdown), cool-down and pot removal, to pump-out of the process tanks to filtration.

**Excluded (covered by other procedures):**
- feedstock supplier approval, receipt, inspection and storage (FOM-001 §7.5);
- filtration, centrifuging, product sampling, testing, release and dispatch (FOM-001 §7.8);
- process water treatment and discharge (FOM-001 §7.8, §7.10);
- off-site char movement, and disposal or recovery of other wastes (FOM-001 §7.10);
- planned maintenance of the kiln, condensers, thermal oxidiser and activated carbon system (FOM-001 §7.11);
- the site-wide Emergency Plan (FOM-001 §7.12). WI-007 covers only the plant shutdown response.

## 3. Inputs & Outputs
| Type | Description | Source / Destination |
|------|-------------|----------------------|
| **Input** | Accepted plastic feedstock (pre-baled, or shredded in bulk bags) | Feedstock storage, after acceptance under FOM-001 §7.5 |
| **Input** | H4 liquid from previous cycles | H4 process tank (WI-010 → WI-003) |
| **Input** | Authorised batch sheet, recipe and thermolysis program | Facility Manager / program library |
| **Input** | Grease, sealant, gaskets, nuts | Approved consumables stores |
| **Input** | Electricity, thermal oxidiser fuel, cooling water, compressed air | Utilities |
| **Output** | H1, H2, H3 hydrocarbon fractions | Filtration units, then testing and release |
| **Output** | H4 hydrocarbon fraction | Kept in the H4 tank for reprocessing |
| **Output** | Char | Char Storage Area, then approved beneficial use or receiver |
| **Output** | Non-condensable gas | Thermal oxidiser (and activated carbon system for fugitive or residual gas) |
| **Output** | Wastes: oily rags, sealant, gaskets, bulk bags, strapping, rejected feedstock | Waste Tracking Register (F-005), then authorised receivers |
| **Output** | Records: batch record, process log, transfer record, incident reports | IMS records ([Section 7](#7-related-documentation)) |

## 4. Process Flow (High Level)
1. Open Pot Lid → 2. Clean the Pot → 3. Load the Pot → 4. Close Pot Lid → 5. Place the Pot in the Kiln → 6. Start the Process → 7. Stop the Process → 8. Lift the Pot → 9. Pump Out from Process Tanks → (back to 1).  
**Emergency Shutdown (WI-007)** can be triggered at any stage, especially during step 6.

```text
            ┌─────────────────────────────────────────────────────────────┐
            │                                                             │
            ▼                                                             │
 ┌──────────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
 │ 1 Open Pot Lid   │──▶│ 2 Clean Pot  │──▶│ 3 Load Pot   │──▶│ 4 Close Pot Lid  │
 │ WI-001  <60 °C   │   │ WI-002       │   │ WI-003       │   │ WI-004  torque x │
 └──────────────────┘   └──────┬───────┘   └──────▲───────┘   └────────┬─────────┘
            ▲                  │ char             │ H4                 │
            │                  ▼                  │                    ▼
 ┌──────────┴───────┐   ┌──────────────┐   ┌──────┴───────┐   ┌──────────────────┐
 │ 8 Lift Pot       │   │ Char storage │   │ 9 Pump Out   │   │ 5 Place in Kiln  │
 │ WI-009  ≤100 °C  │   │ F-005        │   │ WI-010 H1–H3 │   │ WI-005           │
 └──────────▲───────┘   └──────────────┘   │ → filtration │   └────────┬─────────┘
            │                              └──────▲───────┘            │
            │                                     │                    ▼
 ┌──────────┴──────────────────┐                  │           ┌──────────────────┐
 │ 7 Stop Process (WI-008)     │──────────────────┘           │ 6 Start Process  │
 │ program complete → valves   │◀─────────────────────────────│ WI-006 14–16 h   │
 └─────────────────────────────┘                              └────────┬─────────┘
                                                                       │ alarm /
                                                                       ▼ manual
                                                              ┌──────────────────┐
                                                              │ Emergency        │
                                                              │ Shutdown WI-007  │
                                                              └──────────────────┘
```

### 4.1 Step Summary, Controls & Hold Points
| # | Step | Key activities | Critical control / hold point | WI | Records |
|---|------|----------------|-------------------------------|----|---------|
| 1 | Open Pot Lid | Remove 30 nuts with the pneumatic tool at torque x. Lift the lid onto wooden pallets. | **Pot/lid < 60 °C.** Gas test passed. Stop if gas or odour appears and route it to the activated carbon system. | [WI-001](../work-instructions/w01-open-pot-lid.md) | F-001, F-002, F-003 |
| 2 | Clean the Pot | Clean the rim. Remove char in the enclosed bay (scraper + suction). Bag and weigh the char. | Suction runs before the scraper. **Internal inspection (from outside the pot).** No entry into the pot. | [WI-002](../work-instructions/w02-clean-the-pot.md) | F-001, F-002, F-005 |
| 3 | Load the Pot | Load feedstock from bulk bags or bales. Add H4. | **Only lots tagged Accepted.** Mass, fill-height and H4 volume per recipe. | [WI-003](../work-instructions/w03-load-the-pot.md) | F-001, F-002, F-005 |
| 4 | Close Pot Lid | Apply sealant. Align and torque 30 nuts in 3 passes. | **Two-person torque verification, 30 of 30.** | [WI-004](../work-instructions/w04-close-pot-lid.md) | F-001, F-002 |
| 5 | Place the Pot | Crane the pot into the kiln. Make up the column flange. Open the column knife valve. Connect the sensors. | Kiln isolated (LOTO). New gasket. **Facility Manager (or delegate) verifies the flange.** | [WI-005](../work-instructions/w05-place-the-pot.md) | F-001, F-002, F-006 |
| 6 | Start the Process | Open the valves to the condensers, tanks and thermal oxidiser. Verify the baseline. Select the program and press start. | Thermal oxidiser at temperature first. **Full gas path open (F-006).** Program ID matches the batch sheet. Leak check at the first hold. | [WI-006](../work-instructions/w06-start-the-process.md) | F-006, F-007, F-001 |
| 7 | Stopping the Process | Confirm COMPLETE. Close the valves: tanks → condensers → thermal oxidiser → column. | **Pressure at or below the safe-isolation value before the valves close.** | [WI-008](../work-instructions/w08-stopping-the-process.md) | F-006, F-007, F-001 |
| 8 | Lifting the Pot | Disconnect the sensors. Open the column flange. Blank it. Crane the pot to the Cleaning Area. | **Pot ≤ 100 °C.** Knife valves closed. Pneumatic tools only. | [WI-009](../work-instructions/w09-lifting-the-pot.md) | F-001, F-002, F-006 |
| 9 | Pump Out | Transfer H1, H2 and H3 to filtration one at a time. Keep H4. | **Two-person line-up check.** H4 outlet stays closed. Volumes reconciled. | [WI-010](../work-instructions/w10-pump-out-process-tanks.md) | F-008, F-001 |
| E | Emergency Shutdown | Auto-cutoff, or RED button. Immediate response, notification, recovery. | Vent path to treatment stays open. **Facility Manager authorises restart.** | [WI-007](../work-instructions/w07-emergency-shutdown.md) | F-004, F-007 |

## 5. Roles & Responsibilities
| Role | Responsibility |
|------|----------------|
| **Operations Director** | Approves this process and any changes that affect critical limits, significant aspects or permissions (FOM-001 §5.5). Provides resources. |
| **Facility Manager (Process Owner)** | Holds all management roles at the facility. Owns P-001 and its WIs. Authorises batch sheets and recipes. Verifies flange make-up and isolations, or delegates this in writing to a competent Operator. Manages shift handover. Is the Chief Warden and commands the emergency response. Decides on notifications, nonconformity dispositions and restarts. Arranges maintenance. Reviews batch records and KPIs. |
| **Chief Chemist** | Approves specifications, sampling plans and test methods. Holds product release authority and may delegate it in writing to the Quality Analyst. |
| **Quality Analyst** | Signs off the pot inspection hold point. Manages sampling and chain of custody. Assigns product status (awaiting test, released, quarantined) under delegated authority. Maintains calibration of measuring equipment. |
| **Operator: Control Panel function** | Checks the line-up, verifies the baseline, selects the program, monitors the cycle and keeps the process log. |
| **Operator: Field function** | Does the hands-on WI steps, gas testing, valve operation, walk-downs and transfers, and completes the records. |
| **Operator: Crane / Forklift / Dogging function** | Pre-use checks and safe lifting. Holds a High Risk Work Licence where required (OHS Regs 2017, Part 3.6). |
| **Maintenance** (trained Operators, contractors or Hydroxy Systems Australia, authorised by the Facility Manager) | Repairs defects. Returns equipment to service after verification (FOM-001 §7.11). |

Operators are multi-skilled: one Operator may perform several functions in a cycle, but only those they are authorised for in the Training and Competency Matrix (FOM-001 §6.4). Where a WI requires an independent check, the checker must be a different person. Competence for each role and function is defined in the Matrix. Nobody may work unsupervised on a WI until their competence for it has been assessed and recorded.

## 6. Quality & Environmental Requirements (ISO 9001/14001)
### 6.1 Quality Objectives (ISO 9001)
Targets that are not set by law or the licence must be confirmed after a baseline period of three months (FOM-001 §5.4).

| Objective | Measure | Target |
|-----------|---------|--------|
| Batch completed with no deviation | % of batches with no F-004 raised for process deviation | ≥ **[TBC] %** (set from baseline) |
| Batch record complete | % of F-001 forms fully completed and reviewed within 2 working days | **100 %** |
| Traceability | Feedstock lots → batch → H1–H3 / H4 / char linked | **100 %**, tested by a mock trace every 6 months |
| Yield | Recovered liquid (H1–H3) as % of feedstock mass | **[TBC] %** (set from baseline) |
| Mass balance closure | Unaccounted loss per batch | ≤ **[TBC] %** |
| Lid seal integrity | Leaks found at the first-hold leak check | **0** |
| Throughput | Pot cycles completed per week | **[TBC]** |
| Equipment reliability | Unplanned downtime hours per month | **[TBC]** |

### 6.2 Environmental Aspects (ISO 14001)
Significance is assessed in the Environmental Aspects and Impacts Register (FOM-001 §5.2). The ratings below are provisional.

| Aspect | Condition | Impact | Control | Provisional significance |
|--------|-----------|--------|---------|--------------------------|
| Gas or odour when the lid is opened or the flange broken | Normal | Odour, VOC emissions, neighbour amenity | < 60 °C / ≤ 100 °C hold points, gas testing, extraction to the activated carbon system, stop-work rule | **Significant** |
| Non-condensable gas during thermolysis | Normal | Air emissions, greenhouse gases | Thermal oxidiser at temperature before start, licence emission monitoring | **Significant** |
| Fugitive leaks at the lid or flange | Abnormal | VOC emissions, odour, fire | Sealant and torque verification, new gasket every cycle, leak check at the first hold, walk-downs | **Significant** |
| Char dust and char residue | Normal | Dust, solid waste, fire (pyrophoric) | Enclosed bay, suction before scraper, sealed containers, covered storage, waste hierarchy | **Significant** |
| Hydrocarbon (H1–H4) transfer and storage | Normal / abnormal | Soil, stormwater or groundwater contamination | Bunding, earthing, supervised transfers, one fraction at a time, ullage checks, spill kits | **Significant** |
| Energy use (kiln, oxidiser, pumps, compressed air) | Normal | Greenhouse gases, resource depletion | Approved recipes, energy recorded per batch, air leak repair | To be assessed |
| Consumable wastes (rags, sealant, gaskets, bags, strapping) | Normal | Landfill, contamination | Segregation, reuse or recycling of bags and strapping, licensed receivers | Not significant (provisional) |
| Recycling H4 into the next batch | Normal (positive) | Less waste, better yield | Specified H4 ratio per recipe | Positive aspect |
| Fire, explosion, over-pressure, major spill | Emergency | Air, water and soil pollution, community harm | Interlocks, auto-cutoff, RED button, WI-007, Emergency Plan, drills twice a year | **Significant** |

**Life-cycle perspective:** upstream, this process relies on approved feedstock that is free of PVC and other prohibited materials. Downstream, the H1–H3 products and the char must have legitimate, fit-for-purpose uses (BUD, FOM-001 §2), and product information must accompany them when sold.

### 6.3 Risks & Opportunities
Record these in the [risk register](../risk-register/) using the approved matrix (FOM-001 §5.1).

| Risk / Opportunity | Mitigation / Action |
|--------------------|---------------------|
| **Risk:** fire or explosion from residual gas when opening the lid or flange | < 60 °C / ≤ 100 °C hold points, gas testing, pneumatic (non-sparking) tools only, extraction, hot-work permits |
| **Risk:** over-pressure from a closed valve during heating, or valves closed too early at shutdown | F-006 two-person line-up, baseline check, pressure hold point before isolation, interlocks, auto-cutoff |
| **Risk:** dropped load (pot, lid or bulk bag) | Licensed operators, F-002 pre-use checks, exclusion zones, manufacturer to confirm the rating of the lid lugs for the full-pot lift **[TBC]** |
| **Risk:** pyrophoric char fire | Enclosed bay, temperature check, lidded metal containers, extinguisher at the bay |
| **Risk:** confined-space entry to clean the pot | Cleaning done from outside only. Entry prohibited. Any future entry needs a confined space permit (OHS Regs 2017, Part 3.4). |
| **Risk:** prohibited feedstock (e.g. PVC) causing acid gas and off-spec product | Acceptance status gate, visual check at loading, quarantine, supplier corrective action |
| **Risk:** fractions mixed or H4 pumped out | One fraction at a time, two-person line-up check, H4 quality gate |
| **Risk:** lid sensor damage | Lid rested on wooden pallets, sensor inspection at WI-001 and WI-004 |
| **Risk:** odour complaints and licence breach | Stop-work rule for gas or odour, activated carbon media change-out, complaint handling (FOM-001 §7.13) |
| **Opportunity:** use non-condensable gas as process fuel | Assess under change control (FOM-001 §5.5) |
| **Opportunity:** char beneficial use (e.g. soil amendment, carbon product) | Characterise the char and pursue a BUD approval |
| **Opportunity:** recipe optimisation from batch data | Trend the yield and energy per tonne from F-001 and F-007, and review at monthly operations meetings |

### 6.4 Legal & Other Requirements (summary)
| Requirement | Relevance to P-001 |
|-------------|--------------------|
| EPA Victoria Pilot Project Licence PPL000300013 | Air emission, odour, waste and incident notification conditions. Accepted feedstock types. |
| [OHS Act 2004](../assets/regulations/Occupational%20Health%20and%20Safety%20Act%202004.md) s.37–39 | Notifiable incidents, notifying WorkSafe, preserving incident sites (WI-007, F-004) |
| [OHS Regulations 2017](../assets/regulations/Occupational%20Health%20and%20Safety%20Regulations%202017.md) Parts 3.1, 3.2, 3.4, 3.5, 3.6, 4.1 | Manual handling, noise, confined spaces, plant, high risk work licences, hazardous substances |
| [National Waste Policy 2018](../assets/regulations/National%20Waste%20Policy%202018.md) | Waste hierarchy for char and consumable wastes |
| [Excise Act 1901](../assets/regulations/Excise%20Act%20%201901.md) s.50 and [Excise Guidelines for the fuel industry](../assets/regulations/Excise%20Guidelines%20for%20the%20fuel%20industry.md) | Manufacture and stock record-keeping for recovered hydrocarbon fuels **[applicability to be confirmed]** |
| Dangerous Goods (Storage and Handling) Regulations 2022 (Vic) | Storage and transfer of flammable hydrocarbon fractions **[applicability to be confirmed]** |

## 7. Related Documentation
- **Manual:** [FOM-001 Integrated Operations Manual](../manuals/op-manual.md)
- **Work Instructions:**
  - [WI-001 Open Pot Lid](../work-instructions/w01-open-pot-lid.md)
  - [WI-002 Clean the Pot](../work-instructions/w02-clean-the-pot.md)
  - [WI-003 Load the Pot](../work-instructions/w03-load-the-pot.md)
  - [WI-004 Close Pot Lid](../work-instructions/w04-close-pot-lid.md)
  - [WI-005 Place the Pot in the Kiln](../work-instructions/w05-place-the-pot.md)
  - [WI-006 Start the Thermolysis Process](../work-instructions/w06-start-the-process.md)
  - [WI-007 Emergency Shutdown](../work-instructions/w07-emergency-shutdown.md)
  - [WI-008 Stopping the Process](../work-instructions/w08-stopping-the-process.md)
  - [WI-009 Lifting the Pot from the Kiln](../work-instructions/w09-lifting-the-pot.md)
  - [WI-010 Pump Out from Process Tanks](../work-instructions/w10-pump-out-process-tanks.md)
- **Records:**
  - [F-001 Pot Cycle Batch Record](../forms/f01-pot-cycle-batch-record.md)
  - [F-002 Lifting Equipment Pre-use Checklist](../forms/f02-lifting-equipment-pre-use-checklist.md)
  - [F-003 Gas Monitoring Log](../forms/f03-gas-monitoring-log.md)
  - [F-004 Incident, Near Miss & Nonconformance Report](../forms/f04-incident-nonconformance-report.md)
  - [F-005 Waste Tracking Register](../forms/f05-waste-tracking-register.md)
  - [F-006 Valve Line-up & Pre-start Checklist](../forms/f06-valve-lineup-prestart-checklist.md)
  - [F-007 Thermolysis Process Log](../forms/f07-thermolysis-process-log.md)
  - [F-008 Product Transfer Record](../forms/f08-product-transfer-record.md)
- **KPIs:** Monthly Performance Report (FOM-001 §8.1), compiled from F-001, F-004, F-005 and F-007 **[TBC report reference]**
- **Registers:** Risk and Opportunity Register, Environmental Aspects and Impacts Register, Legal and Other Requirements Register, Training and Competency Matrix, Calibration and Verification Register (FOM-001 §10)
- **External:** Plant manufacturer O&M manual, P&ID and valve schedule, approved lifting plan, recipe library, Site Emergency Plan **[TBC references]**

## 8. Revision History
| Version | Date | Description of Change | Author |
|---------|------|------------------------|-------|
| 0.1 | — | Draft high-level process steps (Appendix A) | [Name] |
| 1.0 | 2026-10-02 | Restructured to the process template. Added ISO 9001/14001 requirements and links to WI-001 to WI-010 and F-001 to F-008. | [Name] |
| 1.1 | 2026-10-04 | Roles aligned to the Organisational Structure (Operations Director, Facility Manager, Chief Chemist / Quality Analyst, multi-skilled Operators) | [Name] |

---

## Appendix A: Original Draft Process Steps
*Kept as the source input for this process and its work instructions. Where this appendix and Sections 1–7 or the WIs differ, Sections 1–7 and the WIs take precedence.*

### Open Pot Lid

There are 30 nuts attaching the lid to the Pot. These nuts should be removed using Pneumatic nut remover only (so that the removal process doesn't create heat or sparks). Use torque x while removing the nuts. 

While removing the nuts, consider the following:
- Is the Pot / Lid very hot? What is the temperature? Only start removing when the temperature reaches < 60 degree centigrade.
- Are there any gases coming out of the pot? Stop removing the lid and ensure the gases are sent to activated carbon system.
- Is there any foul odour coming out of the pot? Stop removing the lid and ensure the gases are sent to activated carbon system.

Remove and lift the lid away from the pot. Store / rest the lid on wooden pallets (There are sensors on the bottom / inside of the lid. Storing on wooden pallets avoids damage to the sensors.)

### Clean the Pot  

Clean the grease and sealant from the rim of the pot.  
Pot contains char residues from the previous reaction. Lift the pot into cleaning area. The cleaning area is enclosed to prevent char from flying into the environment. Lift the pot, with crane, and place into cleaning bay. The cleaning bay will be fitted with scraper and suction. The scraper will scrape the side of the pot to loosen the char. The suction will use vaccum to suck the char into bags / containers.

### Load the Pot

Lift the pot and place into Loading area. Load the pot with pre-baled or shredded plastic (from bulk bags opened from bottom).  
Add H4 liquid from the provious process cycles.  

### Close Pot Lid

Apply grease and sealant on the rim of the pot.  
Place the pot lid back on the pot. Align the pot and lid bolt holes.  
Tighten the nuts with Pneumatic nut remover tool only. Use torque x.

### Place the pot

Lift the pot and the lid, suing crane.  
Place the pot in the Kiln.  
Align the lid column flanges with the hot condenser flanges. Tighten the bolts at the flanges.  
Open the knife valve at the condenser flange.  
Connect the sensor cables to the pot lid.  

### Start the process  

Open the knife valves to condensers, tanks, and thermal oxidiser.  
Ensure all sensor cables are connected and monitoring equipment is turned on.  
Switch on the control panel. Check al pressure and temperature readings are at baseline.  
Select thermolysis program and click start.

### Emergency Shutdown

Emergencies could be identified by:
- Alarms
- Out of bound readings (temperature, pressure, voltage)

In case of emergency, an auto-cutoff mechanism is activated. Power to the system is shutdown.  
If emergency shutdown is required for any other reason (manual observation), use the RED emergency shutdown button on the control panel.

### Stopping the process  

After the program is completed, the system shutsdown itself. Monitor the control panel to ensure the process is completed (process status / time will be displayed).  
Close the knife valves for:
- the process tanks
- condensers
- thermal oxidiser
- column flange

### Lifting the pot

After the pot has reached 100 degree centigrade:
- ensure the column flange and hot condenser knife valves are closed
- Open the column flange nuts using pneumatic nut remover.
- attach hooks to pot lid
- lift the pot and the lid to cleaning area, using a crane.

### Pump out from process tanks

Ensure valves from condensers to tanks are closed.  
Open knife valves going out to filtration units.
Switch on the motors to pump out from process tanks into filtration units.
Only pump out H1, H2 and H3 liquids. H4 is to be put back into the pot for re-processing.
