function parisToday() {
    const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Europe/Paris",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).formatToParts(new Date());

    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return new Date(Number(values.year), Number(values.month) - 1, Number(values.day));
}

function localDate(year, month, day) {
    return new Date(year, month - 1, day);
}

function calculateTimeDifference(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    start.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);

    const totalDays = Math.floor((end - start) / 86400000);
    let years = end.getFullYear() - start.getFullYear();
    let anchor = new Date(start);
    anchor.setFullYear(anchor.getFullYear() + years);

    if (anchor > end) {
        years -= 1;
        anchor = new Date(start);
        anchor.setFullYear(anchor.getFullYear() + years);
    }

    let months = end.getMonth() - anchor.getMonth();
    if (end.getDate() < anchor.getDate()) {
        months -= 1;
    }
    if (months < 0) {
        months += 12;
    }

    let monthAnchor = new Date(anchor);
    monthAnchor.setMonth(monthAnchor.getMonth() + months);
    if (monthAnchor > end) {
        months -= 1;
        monthAnchor = new Date(anchor);
        monthAnchor.setMonth(monthAnchor.getMonth() + months);
    }

    const remainingDays = Math.floor((end - monthAnchor) / 86400000);

    return {
        years,
        months,
        weeks: Math.floor(remainingDays / 7),
        days: remainingDays % 7,
        totalDays,
    };
}

function formatDuration(duration) {
    const parts = [];

    if (duration.years > 0) {
        parts.push(`${duration.years} year${duration.years > 1 ? "s" : ""}`);
    }

    if (duration.months > 0) {
        parts.push(`${duration.months} month${duration.months > 1 ? "s" : ""}`);
        const remainingDays = duration.weeks * 7 + duration.days;
        if (remainingDays > 0) {
            parts.push(`${remainingDays} day${remainingDays > 1 ? "s" : ""}`);
        }
    } else {
        if (duration.weeks > 0) {
            parts.push(`${duration.weeks} week${duration.weeks > 1 ? "s" : ""}`);
        }
        if (duration.days > 0) {
            parts.push(`${duration.days} day${duration.days > 1 ? "s" : ""}`);
        }
    }

    if (parts.length === 0) {
        return "0 days";
    }

    if (parts.length === 1) {
        return parts[0];
    }

    return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

function setKrokmouLine(elementId, textBeforeName, textAfterName) {
    const element = document.getElementById(elementId);
    const name = document.createElement("span");
    name.className = "krokmou-name";
    name.textContent = "Krokmou";
    element.replaceChildren(textBeforeName, name, textAfterName);
}

function updateCounters() {
    const now = parisToday();
    const birthDate = localDate(2023, 7, 25);
    const passedDate = localDate(2025, 8, 3);
    const wouldBeAge = calculateTimeDifference(birthDate, now);
    const timeSincePassing = calculateTimeDifference(passedDate, now);

    setKrokmouLine("lifespan", "", " lived to be 2 years, 1 week, 3 days old.");
    document.getElementById("lifespan-days").textContent = "(741 days)";
    setKrokmouLine("would-be", "", ` would be ${formatDuration(wouldBeAge)} old today.`);
    document.getElementById("would-be-days").textContent = `(${wouldBeAge.totalDays + 1} days)`;
    setKrokmouLine("passed", "", ` passed away ${formatDuration(timeSincePassing)} ago.`);
    document.getElementById("passed-days").textContent = `(${timeSincePassing.totalDays} day${timeSincePassing.totalDays === 1 ? "" : "s"} ago)`;
}

updateCounters();
setInterval(updateCounters, 60000);
