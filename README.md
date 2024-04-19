# Read-Only Zoom Phone Collection Script

## Summary

This script uses read-only API calls (GET) to retrieve all active phone users and unassigned phone numbers.  It outputs 5 JSON files:

 - `user_emails.json` - All active users with a Zoom Phone license
	 - Contains a JSON object in the format `user.id : user.email`
     - `string : string`
- `user_extensions.json` - All Zoom Phone users with assigned extensions
	- Contains an object in the format `user.id : user.extension_number`
    - `string : integer`
- `user_phone_numbers.json` - All Zoom Phone users with assigned phone numbers
	- Contains an object in the format `phone_number.assignee.id : phone_number.number`
    - `string : string`
- `unassigned_phone_numbers.json` - All Zoom Phone phone numbers that are not assigned
    - Contains an object in the format `phone_number.id : phone_number.number`
    - `string : string`
- `all_phone_numbers.json` - All Zoom Phone phone numbers
    - Contains an object in the format `phone_number.id : phone_number.number`
    - `string : string`

For understanding of the objects returned by Zoom (structure referred to in the formats above), refer to the API references below.


## API References
The following Zoom Phone API endpoints are used by this script:

[GET  /phone/numbers](https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listAccountPhoneNumbers)

> Returns a list all Zoom Phone numbers in a Zoom account.

[GET  /phone/users](https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listPhoneUsers)

> Returns a list of all of an account's users who are assigned a Zoom Phone license.


## TODO
 - Refactor to pydantic models instead of dictionaries
 - Fork into library with additional functionality