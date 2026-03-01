# Automation Specification

## Purpose

Automate Google account operations using Playwright and BitBrowser fingerprint browser. Handles 2FA management, eligibility verification, age verification, card binding, language settings, and password changes through browser-based automation.

## Requirements

### Requirement: Two-Factor Authentication Setup

The system SHALL automate the setup of TOTP-based 2FA on Google accounts.

#### Scenario: Setup 2FA on a fresh account

- GIVEN a Google account without 2FA enabled
- WHEN the setup_2fa task is executed
- THEN the system navigates to Google security settings via BitBrowser
- AND extracts the TOTP secret key
- AND stores the secret_key in the database
- AND verifies the 2FA setup by entering a generated TOTP code

#### Scenario: Sync 2FA secret to browser

- GIVEN an account with a stored 2FA secret_key
- WHEN sync_2fa_to_browser is executed
- THEN the 2FA secret is configured in the BitBrowser window

### Requirement: Two-Factor Authentication Reset

The system SHALL automate resetting 2FA on Google accounts that already have it enabled.

#### Scenario: Reset existing 2FA

- GIVEN a Google account with 2FA currently enabled
- WHEN the reset_2fa task is executed
- THEN the existing 2FA is disabled
- AND a new 2FA is set up with a fresh secret key
- AND the new secret_key replaces the old one in the database

### Requirement: Eligibility Verification

The system SHALL automate student eligibility verification using SheerID.

#### Scenario: Extract SheerID link

- GIVEN a Google account
- WHEN the eligibility check task is executed
- THEN the system navigates to the eligibility page
- AND extracts the SheerID verification link
- AND stores the link in the database
- AND the account status is updated to "link_ready"

#### Scenario: Account is eligible

- GIVEN an account with an extracted SheerID link
- WHEN the SheerID verification is completed successfully
- THEN the account status is updated to "verified"

#### Scenario: Account is ineligible

- GIVEN an account undergoing eligibility verification
- WHEN the system detects ineligibility
- THEN the account status is updated to "ineligible"

### Requirement: Age Verification

The system SHALL automate age verification using virtual card information.

#### Scenario: Complete age verification

- GIVEN an account requiring age verification and valid card information
- WHEN the age verification task is executed
- THEN the system fills in virtual card details on the verification page
- AND completes the age verification process

### Requirement: Card Binding and Subscription

The system SHALL automate credit card binding and subscription on Google accounts.

#### Scenario: Bind card to account

- GIVEN an account in "verified" status and available virtual card information
- WHEN the bind_card task is executed
- THEN the system navigates through multi-layer iframes to the payment page
- AND fills in virtual card details (card number, expiry month, expiry year, CVV)
- AND completes the card binding process
- AND the account status is updated to "subscribed"

#### Scenario: Card info from database or file

- GIVEN card information configured in database or cards.txt
- WHEN card binding is requested
- THEN the system prioritizes database-configured card info
- AND falls back to cards.txt if database config is not available

### Requirement: Language Setting

The system SHALL auto-switch Google account language to English to reduce automation failures.

#### Scenario: Set language to English

- GIVEN a Google account with non-English language
- WHEN the set_language task is executed
- THEN the account language is changed to English
- AND the language change is verified by checking actual page content

### Requirement: Password Change

The system SHALL automate Google account password changes.

#### Scenario: Change account password

- GIVEN a Google account with current valid credentials
- WHEN the change_password task is executed
- THEN the system navigates to password change page
- AND submits the new password
- AND updates the password in the database

### Requirement: Error Recovery

The system SHOULD handle common automation errors gracefully.

#### Scenario: Login failure detection

- GIVEN an automation task
- WHEN Google login fails (invalid credentials, account locked, etc.)
- THEN the account status is set to "error"
- AND a descriptive error message is stored

#### Scenario: Page navigation timeout

- GIVEN an automation task with page loading
- WHEN a page fails to load within the timeout period
- THEN the task is marked as failed for that account
- AND the error is logged and reported via WebSocket

#### Scenario: CAPTCHA or verification challenge

- GIVEN an automation task navigating Google pages
- WHEN a CAPTCHA or additional verification challenge appears
- THEN the task should detect the challenge
- AND report it as a blocking error for manual intervention
