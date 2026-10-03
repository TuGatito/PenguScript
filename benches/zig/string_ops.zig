const std = @import("std");
pub fn main() !void {
    var acc: i64 = 0;
    var i: usize = 0;
    while (i < 50000) : (i += 1) {
        var buf: [32]u8 = undefined;
        const s = try std.fmt.bufPrint(&buf, "item-{d}", .{i});
        acc += @intCast(s.len);
    }
    const stdout = std.io.getStdOut().writer();
    try stdout.print("{d}\n", .{acc});
}
