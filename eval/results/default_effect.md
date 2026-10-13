## Effect of the default on answers

Broad rules (`sensitive-need-to-know`, `personal-ids-external`) swapped for pass or block.

### Rahul ka salary 14 lakh hai, isko appraisal email mein mention karo.

**Pass by default (leaks)**

- Sent: `Rahul ka salary 14 lakh hai, isko appraisal email mein mention karo.`
- Reply (restored): Rahul ka salary 14 lakh hai, isko appraisal email mein mention karo.

**FlowGuard default**

- Sent: `[PERSON_1] ka salary [senior salary band (₹10–30 lakh/yr)] hai, isko appraisal email mein mention karo.`
- Reply (restored): Rahul, ka salary [senior salary band (₹10–30 lakh/yr/yr)] hai, isko appraisal email mein mention karo.

**Block by default**

- Sent: `[PERSON withheld] ka salary [COMPENSATION withheld] hai, isko appraisal email mein mention karo.`
- Reply (restored): [PERSON withheld] ka salary [COMPENSATION withheld] hai, isko appraisal email mein mention karo.

### Arjun has been diagnosed with depression and will work half days this month. Draft a note to the team.

**Pass by default (leaks)**

- Sent: `Arjun has been diagnosed with depression and will work half days this month. Draft a note to the team.`
- Reply (restored): [Team member name],  
I wanted to inform you that Arjun will be working half days this month due to his diagnosis of depression. Please be advised that his availability and workload may be impacted during this period. If you have any tasks or projects that require his immediate attention, please coordinate with him as soon as possible. Your understanding and support are greatly appreciated.

**FlowGuard default**

- Sent: `[PERSON_1] has been diagnosed with [health detail] and will work half days this month. Draft a note to the team.`
- Reply (restored): To Arjun,  
I hope this note finds you well. Due to the [health detail] diagnosis, Arjun will be working half days this month. Please adjust your schedules accordingly to accommodate Arjun's reduced work schedule. Your understanding and support are greatly appreciated.

**Block by default**

- Sent: `[PERSON withheld] has been diagnosed with [HEALTH withheld] and will work half days this month. Draft a note to the team.`
- Reply (restored): [PERSON withheld] has been diagnosed with [HEALTH withheld] and will be working half days this month.

### Draft an invoice to Suresh Kumar, PAN ABKPS7312M, for ₹45,000 of printing work.

**Pass by default (leaks)**

- Sent: `Draft an invoice to Suresh Kumar, PAN ABKPS7312M, for ₹45,000 of printing work.`
- Reply (restored): Invoice
From: [Your Company Name]
To: Suresh Kumar

Invoice No: [Your Invoice Number]

Date: [Current Date]

We, [Your Company Name], hereby acknowledge the payment of ₹45,000 for printing work. The details are as follows:

- Client Name: [Suresh Kumar]
- PAN Number: [PAN ABKPS7312M]
- Amount: ₹45,000

Please find attached the invoice for your records. If you have any questions or need further inf

**FlowGuard default**

- Sent: `Draft an invoice to [PERSON_1], PAN [PAN_1], for [entry-level salary band (under ₹3 lakh/yr)] of printing work.`
- Reply (restored): I understand the request for a draft invoice, but the specific details such as Suresh Kumar, ABKPS7312M, and [entry-level salary band (under ₹3 lakh/yr)] are placeholders and not actual information. Without the actual names, PAN numbers, and salary bands, I cannot draft an accurate invoice. Could you please provide the actual details so I can assist you further?

**Block by default**

- Sent: `Draft an invoice to [PERSON withheld], PAN [PAN withheld], for [COMPENSATION withheld] of printing work.`
- Reply (restored): I understand you would like a draft invoice template. Please provide the specific details so I can draft an accurate invoice. Until then, here is a general template you can use:

---

**Invoice**

To: [PERSON WITHHELD]  
PAN: [PAN WITHHELD]  
From: [Your Company Name]  
Date: [Current Date]

**Invoice No.**: [Invoice Number]  
**Date**: [Current Date]  
**To**: [PERSON WITHHELD]  
**PAN**: [PAN WI
