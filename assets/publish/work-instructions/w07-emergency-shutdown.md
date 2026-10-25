# Work Instruction: Emergency Shutdown
**WI ID:** WI-007  
**Related Process:** P-001 Thermolysis Pot Cycle ([p01-high-level-process.md](../processes/p01-high-level-process.md))  
**Revision:** 1.1  
**Location:** Whole facility. Primary point of control: Main Control Panel  
**Document Owner:** Facility Manager  
**Approver:** Operations Director  
**Status:** Draft for approval  
**Effective Date:** To be assigned on approval  
**Next Review:** 12 months after approval, after every activation, or after an emergency exercise that finds deficiencies

> [!NOTE]
> This WI supports, and does not replace, the site Emergency Plan (FOM-001 §7.12). Values marked **[TBC]** must be confirmed before approval.

## 1. Purpose & Scope
**Purpose:** To bring the thermolysis plant to a safe state quickly when an emergency is detected, protect people, contain environmental impacts, and meet notification and investigation obligations.

**Scope:** Covers automatic shutdown (auto-cutoff) and manual shutdown using the RED emergency shutdown button, the immediate response, notifications and recovery. Covers every stage of the pot cycle, especially [WI-006](w06-start-the-process.md) (running process).

## 2. Safety & PPE (Critical for Pyrolysis)
> [!IMPORTANT]
> **YOUR SAFETY COMES FIRST.** Do not put yourself at risk to save equipment or product. If there is fire, a major gas release, or someone is injured, **raise the alarm, evacuate to the assembly area and call 000.**
>
> **After shutdown, the pot stays HOT and can still give off gas for many hours.** Keep the gas path to the thermal oxidiser or activated carbon system **open** unless the manufacturer's emergency procedure says otherwise. Closing the vent path on a hot pot can cause over-pressure.

- **Required PPE:** Your normal work PPE. Only trained responders, wearing the PPE the Emergency Plan specifies, may approach a leak or fire.
- **Emergency Stop:** RED emergency shutdown button on the main control panel. Other locations: **[TBC]**.
- **Assembly Area:** **[TBC location]**. Emergency contacts are listed in the Organisation and Emergency Contact Register.

## 3. How to Recognise an Emergency
| Trigger | Examples |
|---------|----------|
| **Alarms** | LEL or gas detector alarm, fire alarm, high pressure, high temperature, tank high-level, thermal oxidiser flame failure. |
| **Readings out of range** | Temperature, pressure or voltage outside the alarm limits **[TBC per recipe/control system]**. |
| **What you see, hear or smell** | Visible smoke or flame, a vapour cloud, strong odour, hissing (leak), liquid spill, unusual noise or vibration, damaged equipment, or an injured person. |

## 4. Environmental Aspects & Controls (ISO 14001)
| Aspect | Potential Impact | Control |
|--------|------------------|---------|
| Uncontrolled gas or odour release | Air pollution, community impact, licence breach | Keep the vent path to treatment open. Monitor at the site boundary. Notify the regulator if required. |
| Spill or loss of containment | Soil, stormwater or groundwater contamination | Close drain isolation valves. Use spill kits and bunds. Recover the material and send it to an authorised receiver. |
| Firewater runoff | Water pollution | Contain it in bunds or the firewater retention area **[TBC]**. Do not release it until it has been tested. |

## 5. Roles, Responsibilities & Competence
| Role | Responsibility |
|------|----------------|
| Any person | Raises the alarm and presses the RED button if safe. Evacuates when told to. |
| Control Panel Operator | Confirms the shutdown, monitors the plant state, and records the event. |
| Chief Warden: Facility Manager (or the Operator appointed as warden if the Facility Manager is off site) | Takes command, makes the evacuation decision, liaises with emergency services, and controls the scene. |
| Facility Manager | Decides on notifications (WorkSafe, EPA), preserves the incident site, leads the investigation, and authorises restart. |

All personnel are trained during induction. Emergency drills are run at least twice a year (FOM-001 §7.12).

## 6. Step-by-Step Procedure
### 6.1 Automatic Shutdown (Auto-Cutoff)
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | The control system detects an alarm or out-of-range reading and cuts power to the system automatically. | The panel shows SHUTDOWN and the kiln heating is OFF. |
| 2 | Panel Operator: confirm the shutdown and note the alarm cause, time and readings. | Recorded on F-007 and F-004. |
| 3 | Go to **6.3 Immediate Response**. | |

### 6.2 Manual Emergency Shutdown
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | If you see an emergency condition (Section 3) that the system has **not** responded to, press the **RED emergency shutdown button** on the control panel, or the nearest field emergency stop. | Power to the system is shut down. |
| 2 | Raise the alarm (radio, verbal, or fire alarm call point) and tell the Chief Warden. | The Chief Warden has acknowledged. |
| 3 | Go to **6.3 Immediate Response**. | |

### 6.3 Immediate Response
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Chief Warden: assess the scene. **Fire, major gas release or injury:** evacuate, call **000** and start the Emergency Plan. | Headcount at the assembly area. |
| 2 | If it is safe, confirm the gas path to the thermal oxidiser or activated carbon system is open and the treatment system is running (or on backup). | Venting is controlled, with no over-pressure. |
| 3 | If there is a spill: close the drain or stormwater isolation valves **[TBC tags]**, contain the spill with the spill kit, and stop the source if safe. | No liquid enters the stormwater system. |
| 4 | Watch the pot temperature and pressure from a safe location. | The trend is downward and stable. |
| 5 | Give first aid if needed, by trained first aiders only. | |
| 6 | Do **not** disturb the incident site except to protect people, give aid, or prevent further harm (OHS Act 2004 s.39). | The scene is preserved. |

### 6.4 Notification & Recording
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Facility Manager: decide whether this is a notifiable incident under the OHS Act 2004 s.37–38. If so, notify **WorkSafe Victoria immediately** (phone 13 23 60), then send written notice within 48 h. | The notification is recorded with the time and reference number. |
| 2 | Decide whether an EPA notification is required under the licence and the Environment Protection Act (e.g. a pollution incident). Notify **EPA Victoria (1300 372 842)** within the required time. | Recorded in the compliance register. |
| 3 | Notify the Operations Director (who informs the CEO of licence matters and the CFO for insurance), and any affected neighbours if there is an off-site impact. | Recorded in the Communication Register. |
| 4 | Complete F-004 before the end of the shift. | F-004 is opened with an event number. |

### 6.5 Recovery & Restart
| Step | Action | Critical Check / Quality Gate |
|------|--------|------------------------------|
| 1 | Investigate the cause in proportion to the actual and potential impact (FOM-001 §9.1). | Root cause identified. |
| 2 | Maintenance repairs and verifies the equipment before it returns to service (FOM-001 §7.11). | Return-to-service record signed. |
| 3 | Decide what happens to the batch in the pot (abort, rework, or reprocess per WI-008/WI-009) and to any off-specification product (FOM-001 §7.9). | Disposition recorded. |
| 4 | **HOLD POINT:** the Facility Manager authorises the restart in writing. | Restart authorised on F-004. |
| 5 | Review the risk register, the aspects register and this WI. Raise corrective actions. | Corrective action is tracked to closure. |

## 7. Troubleshooting
| Issue | Possible Cause | Corrective Action |
|-------|----------------|------------------|
| RED button pressed but the system is still energised | Control circuit fault | Isolate at the main switchboard **[TBC location]** if safe. Evacuate if there is a risk. Treat this as a critical defect. |
| Thermal oxidiser off after shutdown and the pot is still venting | Power loss to the oxidiser | Route the vent to the activated carbon system (manufacturer's procedure). Monitor odour and LEL. Evacuate if the LEL alarm sounds. |
| Pressure still rising after shutdown | Blocked vent path, or exothermic reaction | Evacuate the area. Call 000. Do not approach the pot. |
| False alarm (instrument fault) | Sensor failure | Still treat it as a shutdown. Verify the instrument, record it, and restart only with Facility Manager authorisation. |

## 8. Records to Complete
- F-004 Incident, Near Miss & Nonconformance Report (mandatory for every activation)
- F-007 Thermolysis Process Log: alarm, time, readings
- WorkSafe and EPA notification records (if applicable)
- Emergency drill record (for exercises)

## 9. References
- [FOM-001](../manuals/op-manual.md): §7.12 Emergency preparedness, §7.13 Complaints and incidents, §9.1 Corrective action
- [OHS Act 2004](../assets/regulations/Occupational%20Health%20and%20Safety%20Act%202004.md): s.37 Notifiable incidents, s.38 Duty to notify, s.39 Duty to preserve incident sites
- [OHS Regulations 2017](../assets/regulations/Occupational%20Health%20and%20Safety%20Regulations%202017.md): Part 3.5 Plant, Part 4.1 Hazardous substances
- EPA Victoria Pilot Project Licence PPL000300013 (incident notification conditions)
- Site Emergency Plan **[TBC reference]**
- ISO 9001:2015 cl. 8.7, 10.2; ISO 14001:2015 cl. 8.2, 10.2

## 10. Revision History
| Version | Date | Description of Change | Author |
|---------|------|------------------------|-------|
| 1.0     | 2026-10-02 | Initial Release (developed from P-001 draft) | [Name] |
| 1.1 | 2026-10-04 | Roles aligned to the Organisational Structure (Operations Director, Facility Manager, Chief Chemist / Quality Analyst, multi-skilled Operators) | [Name] |
