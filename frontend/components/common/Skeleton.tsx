interface SkeletonProps {
  width?: string;
  height?: string;
  className?: string;
  rounded?: boolean;
}

export default function Skeleton({
  width = "100%",
  height = "1rem",
  className = "",
  rounded = false,
}: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-[#1E293B] ${rounded ? "rounded-full" : "rounded-lg"} ${className}`}
      style={{ width, height }}
    />
  );
}
