# Read-Only Zoom Phone Collection Script

## Summary

This script uses read-only API calls (GET) to retrieve all active phone users and unassigned phone numbers.  It outputs 3 JSON files:

 - `user_phone_map.json`
	 - Contains an object in the format `userId: phone_number`
- `user_extension_map.json`
	- Contains an object in the format `userId: extension_number`
- `phone_numbers.json`
	- Contains a list of phone numbers

For understanding of the `user` object returned by Zoom, refer to the API references below (particularly the GET endpoint for all users).


## API References
The following Zoom Phone API endpoints are used by this script:

[GET  /phone/numbers](https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listAccountPhoneNumbers)

> Returns a list all Zoom Phone numbers in a Zoom account.

[GET  /phone/users](https://developers.zoom.us/docs/api/rest/reference/phone/methods/#operation/listPhoneUsers)

> Returns a list of all of an account's users who are assigned a Zoom Phone license.


