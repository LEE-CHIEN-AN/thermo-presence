import React, { useState, useRef, useEffect } from "react";

interface DatePickerProps {
  value: string | null; // YYYY-MM-DD format
  onChange: (value: string | null) => void;
  className?: string;
}

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export const DatePicker: React.FC<DatePickerProps> = ({
  value,
  onChange,
  className = "",
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [viewMonth, setViewMonth] = useState(() => {
    if (value) {
      const d = new Date(value + "T00:00:00");
      return { month: d.getMonth(), year: d.getFullYear() };
    }
    const now = new Date();
    return { month: now.getMonth(), year: now.getFullYear() };
  });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const selectedDate = value ? new Date(value + "T00:00:00") : null;

  const getDaysInMonth = (month: number, year: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (month: number, year: number) => {
    return new Date(year, month, 1).getDay();
  };

  const daysInMonth = getDaysInMonth(viewMonth.month, viewMonth.year);
  const firstDay = getFirstDayOfMonth(viewMonth.month, viewMonth.year);
  const prevMonthDays = getDaysInMonth(
    viewMonth.month === 0 ? 11 : viewMonth.month - 1,
    viewMonth.month === 0 ? viewMonth.year - 1 : viewMonth.year
  );

  const days: (number | null)[] = [];
  // Previous month days
  for (let i = firstDay - 1; i >= 0; i--) {
    days.push(prevMonthDays - i);
  }
  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    days.push(i);
  }
  // Next month days to fill the grid
  const remaining = 42 - days.length;
  for (let i = 1; i <= remaining; i++) {
    days.push(i);
  }

  const handleDateClick = (day: number, isPrevMonth: boolean, isNextMonth: boolean) => {
    let month = viewMonth.month;
    let year = viewMonth.year;
    if (isPrevMonth) {
      month = month === 0 ? 11 : month - 1;
      year = month === 11 ? year - 1 : year;
    } else if (isNextMonth) {
      month = month === 11 ? 0 : month + 1;
      year = month === 0 ? year + 1 : year;
    }
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    onChange(dateStr);
    setIsOpen(false);
  };

  const isSelected = (day: number, isPrevMonth: boolean, isNextMonth: boolean) => {
    if (!selectedDate) return false;
    let month = viewMonth.month;
    let year = viewMonth.year;
    if (isPrevMonth) {
      month = month === 0 ? 11 : month - 1;
      year = month === 11 ? year - 1 : year;
    } else if (isNextMonth) {
      month = month === 11 ? 0 : month + 1;
      year = month === 0 ? year + 1 : year;
    }
    return (
      selectedDate.getDate() === day &&
      selectedDate.getMonth() === month &&
      selectedDate.getFullYear() === year
    );
  };

  const displayValue = value
    ? (() => {
        const d = new Date(value + "T00:00:00");
        return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
      })()
    : "Select date";

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-2 py-1 rounded-md bg-slate-900 border border-slate-700 text-sm text-left flex items-center justify-between hover:border-slate-500"
      >
        <span className={value ? "text-slate-100" : "text-slate-500"}>
          {displayValue}
        </span>
        <svg
          className="w-4 h-4 text-slate-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-4 w-80">
          {/* Month/Year Selector */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <select
                value={viewMonth.month}
                onChange={(e) =>
                  setViewMonth({ ...viewMonth, month: parseInt(e.target.value) })
                }
                className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-100"
              >
                {MONTHS.map((month, idx) => (
                  <option key={idx} value={idx}>
                    {month}
                  </option>
                ))}
              </select>
              <select
                value={viewMonth.year}
                onChange={(e) =>
                  setViewMonth({ ...viewMonth, year: parseInt(e.target.value) })
                }
                className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-slate-100"
              >
                {Array.from({ length: 100 }, (_, i) => viewMonth.year - 50 + i).map(
                  (year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  )
                )}
              </select>
            </div>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-1">
            {/* Weekday headers */}
            {WEEKDAYS.map((day) => (
              <div
                key={day}
                className="text-center text-xs font-medium text-slate-400 py-1"
              >
                {day}
              </div>
            ))}

            {/* Calendar days */}
            {days.map((day, idx) => {
              if (day === null) return <div key={idx} />;
              const isPrevMonth = idx < firstDay;
              const isNextMonth = idx >= firstDay + daysInMonth;
              const selected = isSelected(day, isPrevMonth, isNextMonth);
              const isToday = (() => {
                const today = new Date();
                let month = viewMonth.month;
                let year = viewMonth.year;
                if (isPrevMonth) {
                  month = month === 0 ? 11 : month - 1;
                  year = month === 11 ? year - 1 : year;
                } else if (isNextMonth) {
                  month = month === 11 ? 0 : month + 1;
                  year = month === 0 ? year + 1 : year;
                }
                return (
                  day === today.getDate() &&
                  month === today.getMonth() &&
                  year === today.getFullYear()
                );
              })();

              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleDateClick(day, isPrevMonth, isNextMonth)}
                  className={`
                    aspect-square flex items-center justify-center text-sm rounded
                    ${
                      selected
                        ? "bg-sky-600 text-white font-semibold"
                        : isPrevMonth || isNextMonth
                        ? "text-slate-500 hover:bg-slate-800"
                        : isToday
                        ? "bg-slate-800 text-slate-200 font-medium hover:bg-slate-700"
                        : "text-slate-200 hover:bg-slate-800"
                    }
                  `}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

