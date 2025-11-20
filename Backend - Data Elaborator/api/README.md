# Earthquake Monitoring System

## description

API to manage zones, misurators and alert_misurations

## Exposed APIs


### Get Zones


Get all zones

Parameters:
- N/A

Returns:
- List of all zones

| Method | URL |
|--------|-----|
| GET | /zones/ |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| skip | query | skip first 'skip' records | Optional |
| limit | query | show a maximum of 'limit' records | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| List | List | List of all zones | 

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error Message |

---

### Create Zone


Create a new zone

Parameters:
- City

Returns:
- Newly Created Zone

| Method | URL |
|--------|-----|
| POST | /zones/ |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| city |  query  | Connect city to the zone | Required |

##### Request Body
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| city | string | City connected to the zone | Required |

##### Response (201)
| Field | Type | Description |
|-------|------|-------------|
| city | string | City connected to the record |
| id | integer | Zone ID |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Zone


Get a specific zone by id

Parameters
- Zone ID

Returns
- Single Zone

| Method | URL |
|--------|-----|
| GET | /zones/{zone_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| zone_id | path | Id of the zone to find | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| city | string | City connected to the zone |
| id | integer | Zone ID |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Update Zone


Update a zone by id

Parameters:
- Zone ID
- City

Returns:
- Updated Zone

| Method | URL |
|--------|-----|
| PUT | /zones/{zone_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| zone_id | path | Id of the zone to find | Required |

##### Request Body
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| city | N/A | New city to connect to the zone | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| city | string | City connected the zone |
| id | integer | Id of the zone |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Delete Zone


Delete a Zone

Parameters:
- Zone ID

Returns:
- Succesfulness msg

| Method | URL |
|--------|-----|
| DELETE | /zones/{zone_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| zone_id | path | Id of the zone to delete | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| message | string | Succesfulness message |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Misurators


Get all misurators with optional filters

Parameters:
- N/A

Returns:
- List of Misurators

| Method | URL |
|--------|-----|
| GET | /misurators/ |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| skip | query | Skip first 'skip' records | Optional |
| limit | query | Show a maximum of 'limit' records | Optional |
| active | query | Get only active misurators | Optional |
| zone_id | query | Get misurators of a specific zone | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| List  | List | List of all misurators (based on filters) |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Create Misurator


Create new misurator

Parameters:
- active
- zone_id

Returns:
- Created Misurator

| Method | URL |
|--------|-----|
| POST | /misurators/ |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| active | query | Whether the misurator is active or not | Required |
| zone_id | query | Id of the connected zone | Required |

##### Request Body
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| active | boolean | Whether the misurator is active or not  | Required |
| zone_id | integer | Id of the connected zone | Required |

##### Response (201)
| Field | Type | Description |
|-------|------|-------------|
| active | boolean | Whether the misurator is active or not |
| zone_id | integer | Id of the connected zone |
| id | integer | Id of the record |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Misurator


Get specific misurator by id

Parameters:
- Misurator ID

Returns:
- Specific Misurator

| Method | URL |
|--------|-----|
| GET | /misurators/{misurator_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misurator_id | path | Id of the misurator to find | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| active | boolean | Whether the misurator is active or not |
| zone_id | integer | Id of the connected zone |
| id | integer | Id of the record  |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Update Misurator


Update Misurator

Parameters:
- active
- zone_id

Returns:
- Updated Misurator

| Method | URL |
|--------|-----|
| PUT | /misurators/{misurator_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misurator_id | path | Id of the misurator to update | Required |

##### Request Body
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| active | boolean | Wether the misurator is active or not | Optional |
| zone_id | string | Id of the connected zone | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| active | boolean | Wether the misurator is active or not |
| zone_id | integer | Id of the connected zone |
| id | integer | Id of the record |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Activate Misurator


Activate misurator

Parameters:
- Misurator ID

Returns:
- Succesfulness msg

| Method | URL |
|--------|-----|
| PUT | /misurators/{misurator_id}/activate |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misurator_id | path | Id of the misurator to activate | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| message | string | Succesfulness message |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Deactivate Misurator


Deactivate misurator

Parameters:
- Misurator ID

Returns:
- Succesfullness msg

| Method | URL |
|--------|-----|
| PUT | /misurators/{misurator_id}/deactivate |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misurator_id | path | Id of the misurator to deactivate | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| message | string | Succesfulness message |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Misurations


Get all misurations with optional filters

Parameters:
- Skip  (skip x records)
- Limit (maximum records)

Returns:
- List of all zones

| Method | URL |
|--------|-----|
| GET | /misurations/ |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| skip | query | Skip first 'skip' records | Optional |
| limit | query | Show a maximum of 'limit' records | Optional |
| misurator_id | query | Id of the connected misurator | Optional |
| start_date | query | Starting date | Optional |
| end_date | query | Final date | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| List  | List | List of all misurators (based on filters) |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Create Misuration


Create a new misuration

Parameters:
- value
- misurator_id

Returns:
- Created Misuration

| Method | URL |
|--------|-----|
| POST | /misurations/ |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| value | query | Value of the misuration | Required |
| misurator_id | query | Id of the connected misurator | Required |

##### Request Body
| Field | Type | Description | Required |
|-------|------|-------------|----------|
| value | integer | Value of the misuration | Required |
| misurator_id | integer | Id of the connected misurator | Required |

##### Response (201)
| Field | Type | Description |
|-------|------|-------------|
| value | integer | Value of the misuration |
| misurator_id | integer | Id of the connected misurator |
| id | integer | Id of the record |
| created_at | string | Creation timestamp |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Misuration


Get specific misuration by id

Parameters:
- Misuration ID

Returns:
- Specific Misuration

| Method | URL |
|--------|-----|
| GET | /misurations/{misuration_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misuration_id | path | Id of the record to find | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| value | integer | Value of the misuration |
| misurator_id | integer | Id of the misurator |
| id | integer | Id of the record |
| created_at | string | Creation timestamp |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Zone Misurators


Get all misurators of a specific zone

Parameters:
- zone_id

Returns:
- List of all Misurators of a specific Zone

| Method | URL |
|--------|-----|
| GET | /zones/{zone_id}/misurators |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| zone_id | path | Id of the zone to find | Required |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| List  | List | List of all misurators of the specified zone |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Misurator Misurations


Get all misurations of a specific misurator

Parameters:
- misurator_id
- hours

Returns:
- List of all Misurations of specific Misurator in the last X Hours

| Method | URL |
|--------|-----|
| GET | /misurators/{misurator_id}/misurations |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misurator_id | path | Id of the misurator to find | Required |
| hours | query | Maximum hours range to check | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| List  | List | List of all misurations of a specific misurator in the last 'hours' hours |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Get Zones Stats


Get statistics for all zones

Parameters:
- N/A

Returns:
- List of stats of all zones

| Method | URL |
|--------|-----|
| GET | /stats/zones |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|


##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| List  | List | List of all zones with these attributes: |
| zone_id | integer | Id of the zone |
| city | string | Connected city |
| total_misurators | integer | count of all misurators |
| active_misurators | integer | count of all active misurators |

---

### Get Misurator Stats


Gets stats of a specific misurator

Parameters:
- Misurator ID

Returns:
- misurator_id
- total_misurations
- avg_value
- min_value
- max_value
- period_days

| Method | URL |
|--------|-----|
| GET | /stats/misurators/{misurator_id} |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|
| misurator_id | path | Id of the misurator to find | Required |
| days | query | Query last 'days' days | Optional |

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| misurator_id | integer | Id of the record |
| total_misurations | integer | Count of all misurations |
| avg_value | float | Average misurations value |
| min_value | integer | Minimum misuration value |
| max_value | integer | Maximum misuration value |
| period_days | integer | Total days of misuration |

##### Response (422)
| Field | Type | Description |
|-------|------|-------------|
| detail | array | Error message |

---

### Read Root




| Method | URL |
|--------|-----|
| GET | / |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| message | string | App title |
| version | string | App version |
| endpoints | List | List of all endpoints of the app - below |
| zones | string | Zones endpoint |
| Misurators | string | Misurators endpoint |
| Misurations | string | Misurations endpoint |
| Stats | string | Statistics endpoint |

---

### Health Check


Application and Database health check

Parameters:
- N/A

Returns:
- status
- connection
- timestamp

| Method | URL |
|--------|-----|
| GET | /health |

#### Parameters
| Name | In | Description | Required |
|------|----|-------------|----------|

##### Response (200)
| Field | Type | Description |
|-------|------|-------------|
| status | string | Database status (healthy) |
| database | string | Database status (connected) |
| timestamp | DateTime | Check timestamp |

---
